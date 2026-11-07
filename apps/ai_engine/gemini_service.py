import json
import logging
import requests
from django.conf import settings
from django.utils import timezone
from .models import AiAnalysis
from apps.recommendations.models import AiRecommendation, RecommendationVersion
from apps.wellness.models import WellnessSchedule, WellnessActivity
from apps.notifications.models import Notification
from apps.accounts.models import AuditLog, User
from apps.physicians.models import PhysicianProfile
from datetime import date, time, timedelta

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are the GabAI Clinical Assistant.
You assist qualified psychiatrists and physicians by analyzing patient-reported mental health questionnaire responses.

MANDATORY CLINICAL GUARDRAILS:
1. NEVER independently diagnose a mental disorder or condition. Use phrases like "The patient reported elevated symptoms consistent with...", "Reported indicators warrant physician evaluation".
2. NEVER prescribe or recommend specific medications or pharmaceutical doses.
3. NEVER classify a patient as completely mentally healthy solely because of a low screening score.
4. Distinguish patient-reported subjective symptoms from physician-confirmed objective findings.
5. All outputs will be reviewed and approved by a licensed physician before release to the patient.
6. If acute safety concerns (suicidal intent/plan) are noted, state that immediate safety escalation is triggered.
7. Return ONLY valid JSON matching the requested structure.
"""

def generate_ai_analysis_and_recommendations(assessment):
    """
    Analyzes assessment data and generates structured AI analysis,
    personalized recommendations (Pathway A or Pathway B), and initial wellness schedule.
    """
    patient = assessment.patient
    user = patient.user

    # Gather assessment data and category indicators
    screening_results = assessment.screening_results.select_related('category').all()
    responses = assessment.responses.select_related('question__category').all()

    elevated_categories = []
    freq_symptoms = []
    
    for r in responses:
        if r.numeric_score >= 2: # 'More than half the days' or 'Nearly every day'
            freq_symptoms.append(f"{r.question.category.name}: {r.question.question_text}")

    for res in screening_results:
        if res.is_elevated:
            elevated_categories.append({
                'category': res.category.name,
                'score_pct': res.score_percentage,
                'severity': res.severity_level
            })

    # Determine pathway:
    # Pathway B if any category is MODERATE, ELEVATED, HIGH, or PHQ-9 >= 10, or GAD-7 >= 10, or safety flag
    is_pathway_b = (
        len(elevated_categories) > 0 or 
        (assessment.phq9_score and assessment.phq9_score >= 10) or 
        (assessment.gad7_score and assessment.gad7_score >= 10) or
        assessment.has_safety_flag
    )
    pathway = 'PATHWAY_B' if is_pathway_b else 'PATHWAY_A'

    # Try Gemini API if key is present
    ai_data = None
    if settings.GEMINI_API_KEY:
        try:
            ai_data = _call_gemini_api(assessment, patient, elevated_categories, freq_symptoms, pathway)
        except Exception as e:
            logger.warning(f"Gemini API invocation failed, switching to clinical heuristic engine: {e}")

    if not ai_data:
        ai_data = _generate_clinical_heuristics(assessment, patient, elevated_categories, freq_symptoms, pathway)

    # 1. Save AiAnalysis model
    ai_analysis, _ = AiAnalysis.objects.update_or_create(
        assessment=assessment,
        defaults={
            'analysis_pathway': pathway,
            'frequently_reported_symptoms': ai_data.get('frequently_reported_symptoms', freq_symptoms[:8]),
            'elevated_categories': [c['category'] if isinstance(c, dict) else c for c in elevated_categories],
            'identified_patterns': ai_data.get('identified_patterns', 'Observed patterns based on reported screening items.'),
            'daily_activity_effects': ai_data.get('daily_activity_effects', 'Reported moderate fatigue and routine difficulties.'),
            'areas_for_investigation': ai_data.get('areas_for_investigation', 'Physician clinical interview regarding lifestyle and stressors.'),
            'missing_or_incomplete_notes': 'All mandatory items completed.',
            'safety_concerns_flagged': assessment.has_safety_flag,
            'safety_summary': "Immediate crisis protocol active." if assessment.has_safety_flag else "No acute safety markers detected.",
            'physician_readable_summary': ai_data.get('physician_summary', ''),
            'is_diagnostic': False,
            'model_used': 'GabAI Gemini 1.5 Pro Clinical Engine' if settings.GEMINI_API_KEY else 'GabAI Clinical Rule Engine'
        }
    )

    # 2. Save AiRecommendation model (Default: PENDING_APPROVAL, hidden from patient)
    recommendation, _ = AiRecommendation.objects.update_or_create(
        assessment=assessment,
        patient=patient,
        defaults={
            'pathway': pathway,
            'status': 'PENDING_APPROVAL',
            'title': ai_data.get('recommendation_title', 'Personalized Mental Wellness & Care Plan'),
            'summary_content': ai_data.get('recommendation_summary', ''),
            'daily_schedule_plan': ai_data.get('daily_schedule', []),
            'weekly_activities_plan': ai_data.get('weekly_activities', []),
            'preventive_strategies': ai_data.get('preventive_strategies', []),
            'coping_strategies': ai_data.get('coping_strategies', []),
            'lifestyle_modifications': ai_data.get('lifestyle_modifications', ''),
            'follow_up_guidance': ai_data.get('follow_up_guidance', 'Follow-up with physician recommended in 2-4 weeks.'),
            'current_version': 1,
            'is_visible_to_patient': False # STRICT REQUIREMENT: Hidden until physician approves!
        }
    )

    # 3. Create RecommendationVersion 1 (Original AI)
    RecommendationVersion.objects.update_or_create(
        recommendation=recommendation,
        version_number=1,
        defaults={
            'modification_type': 'AI_INITIAL',
            'title': recommendation.title,
            'summary_content': recommendation.summary_content,
            'daily_schedule_plan': recommendation.daily_schedule_plan,
            'weekly_activities_plan': recommendation.weekly_activities_plan,
            'coping_strategies': recommendation.coping_strategies,
            'preventive_strategies': recommendation.preventive_strategies,
            'change_summary': 'Initial AI-generated draft awaiting physician evaluation.'
        }
    )

    # 4. Generate Wellness Schedule and Activities
    schedule, _ = WellnessSchedule.objects.update_or_create(
        patient=patient,
        recommendation=recommendation,
        defaults={
            'title': f"Wellness Schedule: {recommendation.title}"[:180],
            'start_date': date.today(),
            'end_date': date.today() + timedelta(days=14),
            'status': 'ACTIVE',
            'is_physician_approved': False
        }
    )

    # Populate daily activities from schedule plan
    # Clear existing pending activities for fresh plan
    WellnessActivity.objects.filter(schedule=schedule, status='PENDING').delete()

    order_idx = 1
    for act in ai_data.get('daily_schedule', []):
        try:
            time_parts = act.get('time', '08:00').split(':')
            act_time = time(int(time_parts[0]), int(time_parts[1]) if len(time_parts) > 1 else 0)
        except Exception:
            act_time = time(8, 0)

        WellnessActivity.objects.create(
            schedule=schedule,
            patient=patient,
            title=act.get('activity', 'Mindfulness Session'),
            description=act.get('description', 'Healthy routine practice.'),
            category=act.get('category', 'MINDFULNESS'),
            scheduled_date=date.today(),
            start_time=act_time,
            end_time=(timezone.datetime.combine(date.today(), act_time) + timedelta(minutes=30)).time(),
            purpose=act.get('purpose', 'Wellness balance and emotional regulation'),
            status='PENDING',
            is_weekly=False,
            order=order_idx
        )
        order_idx += 1

    # Populate weekly activities
    for w_act in ai_data.get('weekly_activities', []):
        WellnessActivity.objects.create(
            schedule=schedule,
            patient=patient,
            title=w_act.get('activity', 'Weekend Outdoor Recreation'),
            description=w_act.get('description', 'Weekly wellness milestone.'),
            category='HOBBY',
            scheduled_date=date.today() + timedelta(days=5),
            start_time=time(10, 0),
            end_time=time(11, 30),
            purpose=w_act.get('purpose', 'Sustained mood balance and stress relief'),
            status='PENDING',
            is_weekly=True,
            order=order_idx
        )
        order_idx += 1

    # Update assessment status
    assessment.status = 'ANALYZED'
    assessment.save(update_fields=['status', 'updated_at'])

    # 5. Notify Physician about review needed
    physicians_to_notify = []
    if patient.assigned_physician:
        physicians_to_notify.append(patient.assigned_physician.user)
    else:
        for p in PhysicianProfile.objects.filter(is_verified=True)[:3]:
            physicians_to_notify.append(p.user)

    for phys_user in physicians_to_notify:
        Notification.send(
            recipient=phys_user,
            notification_type='ASSESSMENT_READY',
            title=f"AI Recommendation Awaiting Review: Patient {patient.user.get_full_name()}",
            message=f"Assessment #{assessment.id} for {patient.user.get_full_name()} has been analyzed. Please review, modify, or approve the generated care guidance.",
            action_url=f"/recommendations/review/{recommendation.id}/",
            is_urgent=assessment.has_safety_flag
        )

    # Log to AuditLog
    AuditLog.objects.create(
        user=user,
        action='AI_RECOMMENDATION_GENERATED',
        entity_name='AiRecommendation',
        entity_id=str(recommendation.id),
        details=f"Generated {pathway} recommendation #{recommendation.id}. Status: PENDING_APPROVAL."
    )

    return recommendation


def _generate_clinical_heuristics(assessment, patient, elevated_categories, freq_symptoms, pathway):
    """
    Robust clinical heuristic engine that generates accurate,
    evidence-based structured mental wellness schedules and recommendations.
    """
    age = patient.age or 26
    occupation = patient.occupation or "Professional / Student"
    interests = patient.personal_interests or "walking, reading, listening to music"
    elevated_names = [c['category'] if isinstance(c, dict) else c for c in elevated_categories]

    if pathway == 'PATHWAY_A':
        # PATHWAY A: Preventive Mental Wellness Program
        title = f"Personalized Preventive Mental Wellness Program"
        summary = (
            f"The patient's screening indicates low overall reported distress without elevated clinical screening flags. "
            f"A proactive preventive wellness regimen has been formulated to reinforce resilience, support daily vitality, "
            f"and maintain emotional well-being aligned with their routine ({patient.work_or_school_schedule})."
        )
        physician_summary = (
            f"Patient {patient.user.get_full_name()} (Age {age}, {occupation}) screened within minimal concern ranges. "
            f"PHQ-9 score: {assessment.phq9_score or 0}/27 (Minimal); GAD-7 score: {assessment.gad7_score or 0}/21 (Minimal). "
            f"No acute safety concerns detected. Preventive wellness program generated focusing on routine stability, "
            f"exercise, mindfulness, and healthy sleep hygiene. Awaiting physician validation."
        )
        daily_schedule = [
            {
                'time': '07:00',
                'activity': 'Morning Hydration & Gentle Movement',
                'description': '15 minutes of light stretching or outdoor walk with daylight exposure to anchor circadian rhythm.',
                'category': 'EXERCISE',
                'purpose': 'Cortisol awakening response regulation and physical activation'
            },
            {
                'time': '07:45',
                'activity': 'Mindful Balanced Breakfast',
                'description': 'Nutrient-rich meal with adequate protein, complex carbohydrates, and hydration without excessive caffeine.',
                'category': 'NUTRITION',
                'purpose': 'Sustained cognitive energy and blood glucose stability'
            },
            {
                'time': '10:30',
                'activity': 'Micro-Break & Posture Reset',
                'description': '5-minute screen pause, neck and shoulder rolls, 10 deep belly breaths.',
                'category': 'WORK_BREAK',
                'purpose': 'Mitigation of ocular fatigue and sympathetic nervous system calming'
            },
            {
                'time': '12:30',
                'activity': 'Mindful Lunch & Social Connection',
                'description': 'Eat away from desk or workspace; casual conversation with a colleague, friend, or family member.',
                'category': 'SOCIAL',
                'purpose': 'Social buffering and cognitive recovery'
            },
            {
                'time': '16:00',
                'activity': 'Afternoon Focus Pause & Hydration',
                'description': 'Hydrate with herbal tea or water; brief mindfulness grounding technique (5-4-3-2-1 sensory check).',
                'category': 'MINDFULNESS',
                'purpose': 'Afternoon mental clarity and sensory recentering'
            },
            {
                'time': '18:30',
                'activity': 'Recreational Hobby & Personal Interests',
                'description': f'Engage in chosen hobby ({interests}) or light recreational activity.',
                'category': 'HOBBY',
                'purpose': 'Intrinsic motivation support and decompression from daily responsibilities'
            },
            {
                'time': '21:30',
                'activity': 'Evening Reflection Journaling',
                'description': 'Write 3 positive experiences or gratitude observations from today; plan 2 priorities for tomorrow.',
                'category': 'JOURNALING',
                'purpose': 'Cognitive closure, stress offloading, and positive emotional appraisal'
            },
            {
                'time': '22:30',
                'activity': 'Digital Sunset & Sleep Hygiene Routine',
                'description': 'Dim ambient lights, disconnect from blue-light screens 30-45 minutes before sleep; cool, dark bedroom environment.',
                'category': 'SLEEP_HYGIENE',
                'purpose': 'Endogenous melatonin production and restorative slow-wave sleep'
            }
        ]
        weekly_activities = [
            {
                'activity': 'Aerobic Outdoor Exercise (30-45 mins)',
                'description': 'Brisk walking, jogging, cycling, or swimming in a natural or park environment.',
                'purpose': 'Cardiovascular health and endorphin release'
            },
            {
                'activity': 'Creative & Cultural Engagement',
                'description': 'Music, art, reading, cooking a new recipe, or crafting without performance pressure.',
                'purpose': 'Neuroplasticity stimulation and affective restoration'
            },
            {
                'activity': 'Social & Family Gathering',
                'description': 'Intentional meaningful social time with supportive friends or loved ones.',
                'purpose': 'Emotional safety and community connection'
            },
            {
                'activity': 'Weekly Self-Reflection & Planning',
                'description': '30-minute review of weekly wins, emotional check-in, and boundary setting for the upcoming week.',
                'purpose': 'Self-efficacy enhancement and proactive stress modulation'
            }
        ]
        preventive_strategies = [
            "Maintain consistent wake-up and sleep times within a 30-minute variance, even on weekends.",
            "Practice the 20-20-20 rule during screen use: every 20 minutes, gaze at an object 20 feet away for 20 seconds.",
            "Incorporate box breathing (4s inhale, 4s hold, 4s exhale, 4s hold) during transitional moments of the day.",
            "Protect at least 60 minutes daily for personal restorative activities free from professional obligations.",
            "Reach out to healthcare professionals or campus/workplace counselors if mood changes persist for >2 weeks."
        ]
        coping_strategies = [
            "Cognitive reframing for unexpected daily disruptions.",
            "Progressive muscle relaxation (PMR) when feeling physical muscle tension."
        ]
        lifestyle_modifications = "Prioritize hydration (2-2.5L daily), moderate caffeine consumption after 2:00 PM, and encourage regular outdoor exposure."
    else:
        # PATHWAY B: Supportive Guidance for Reported Mental Health Concerns
        primary_concerns = ", ".join(elevated_names) if elevated_names else "elevated stress and mood concerns"
        if len(primary_concerns) > 150:
            primary_concerns = primary_concerns[:147] + "..."
        title = f"Supportive Care & Symptom Management ({primary_concerns})"[:240]
        summary = (
            f"The patient's screening indicates elevated indicators in: {primary_concerns}. "
            f"This supportive plan provides evidence-informed, non-diagnostic coping strategies, "
            f"structured routines, and encourages professional clinical evaluation by an attending physician."
        )
        physician_summary = (
            f"Patient {patient.user.get_full_name()} (Age {age}, {occupation}) screened with elevated concerns in: {primary_concerns}. "
            f"PHQ-9 score: {assessment.phq9_score or 'N/A'}/27 ({assessment.phq9_severity or 'Evaluated'}); "
            f"GAD-7 score: {assessment.gad7_score or 'N/A'}/21 ({assessment.gad7_severity or 'Evaluated'}). "
            f"Frequently reported symptoms: {len(freq_symptoms)} items flagged frequently. "
            f"{'CRITICAL SAFETY CONCERN: Immediate emergency protocol is active.' if assessment.has_safety_flag else 'No acute suicidal plan/intent noted.'} "
            f"Recommended clinical actions: Comprehensive clinical diagnostic interview, evaluation of functional impairment, "
            f"and review of tailored coping recommendations before patient release."
        )

        daily_schedule = [
            {
                'time': '07:30',
                'activity': 'Gentle Grounding & Morning Sunlight',
                'description': 'Sit by a bright window or outside for 10-15 minutes; practice 4-7-8 calming breathing.',
                'category': 'RELAXATION',
                'purpose': 'Nervous system down-regulation and morning circadian anchoring'
            },
            {
                'time': '08:15',
                'activity': 'Low-Stress Nourishment',
                'description': 'Light, balanced meal; warm herbal tea (chamomile or peppermint). Avoid high-caffeine energy drinks.',
                'category': 'NUTRITION',
                'purpose': 'Stabilizing physical equilibrium without exacerbating palpitations or jitteriness'
            },
            {
                'time': '10:00',
                'activity': 'Micro-Task Chunking (Pomodoro 25/5)',
                'description': 'Break work or academic duties into small 20-25 minute manageable increments with mandatory 5-minute pauses.',
                'category': 'WORK_BREAK',
                'purpose': 'Reducing cognitive overwhelm and supporting executive functioning'
            },
            {
                'time': '13:00',
                'activity': 'Calming Midday Reset',
                'description': 'Step into a quiet environment, listen to nature sounds or soothing instrumental music; sensory reset.',
                'category': 'MINDFULNESS',
                'purpose': 'Sensory decompression and emotional pacing'
            },
            {
                'time': '17:30',
                'activity': 'Low-Intensity Movement (Walking)',
                'description': 'A 20-minute rhythmic walk at a comfortable pace without strenuous pressure.',
                'category': 'EXERCISE',
                'purpose': 'Somatic discharge of accumulated muscle tension and mild mood enhancement'
            },
            {
                'time': '20:30',
                'activity': 'Worry Dump / Emotional Journaling',
                'description': 'Dedicate 10 minutes to write down racing thoughts onto paper, then physically close the notebook for the night.',
                'category': 'JOURNALING',
                'purpose': 'Cognitive externalization of rumination and intrusive worries'
            },
            {
                'time': '22:00',
                'activity': 'Structured Sleep De-escalation',
                'description': 'Progressive muscle relaxation in bed; dim lighting; keep phone charging outside arm reach.',
                'category': 'SLEEP_HYGIENE',
                'purpose': 'Sleep latency reduction and parasympathetic nervous system activation'
            }
        ]

        weekly_activities = [
            {
                'activity': 'Scheduled Professional Clinical Consultation',
                'description': 'Attend scheduled appointment with physician/psychiatrist to discuss formal clinical evaluation and care.',
                'purpose': 'Professional clinical diagnostic evaluation and medical oversight'
            },
            {
                'activity': 'Low-Demand Nature Immersion',
                'description': 'Spends 45 minutes in a botanical garden, quiet park, or green space with minimal crowd exposure.',
                'purpose': 'Attention Restoration Theory (ART) benefits and stress hormone reduction'
            },
            {
                'activity': 'Safe-Space Social Contact',
                'description': 'One low-pressure connection with a trusted person who does not demand emotional performance.',
                'purpose': 'Combating social isolation while respecting energy boundaries'
            }
        ]

        coping_strategies = []
        if 'Anxiety' in str(elevated_names) or (assessment.gad7_score and assessment.gad7_score >= 8):
            coping_strategies.extend([
                "Guided Box Breathing: Inhale for 4s, hold 4s, exhale 4s, hold 4s. Repeat for 4 cycles when acute anxiety rises.",
                "5-4-3-2-1 Sensory Grounding: Acknowledge 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste."
            ])
        if 'Depression' in str(elevated_names) or (assessment.phq9_score and assessment.phq9_score >= 8):
            coping_strategies.extend([
                "Behavioral Activation: Engage in small, scheduled rewarding activities regardless of transient lack of initial motivation.",
                "Opposite Action: When urge to isolate appears, take one small gentle step toward contact or stepping outside."
            ])
        if 'Stress' in str(elevated_names) or 'Burnout' in str(elevated_names):
            coping_strategies.append(
                "Workload Boundary Setting: Identify top 2 non-negotiable tasks per day; explicitly delegate or defer non-urgent obligations."
            )
        if 'ADHD' in str(elevated_names):
            coping_strategies.append(
                "Visual Task Externalization: Use high-visibility sticky notes, digital timers, and color-coded priority blocks for tasks."
            )
        if 'Autism' in str(elevated_names):
            coping_strategies.append(
                "Sensory Environment Adjustments: Utilize noise-dampening earplugs, soft lighting, and scheduled low-stimulation quiet intervals."
            )
        if not coping_strategies:
            coping_strategies = [
                "Guided diaphragm breathing exercises for autonomic nervous system stabilization.",
                "Structured daily task pacing to prevent cognitive fatigue and overwhelm."
            ]

        preventive_strategies = [
            "Do not stop, start, or alter any prescribed psychiatric or medical treatment without physician direction.",
            "Recognize personal early-warning indicators (e.g. sleep disruption, irritability, withdrawal) and notify care team.",
            "Establish predictable transition routines between work/study obligations and home rest.",
            "Limit exposure to triggering sensationalist news or high-conflict online environments."
        ]
        lifestyle_modifications = "Maintain stable nutritional intake, avoid alcohol or recreational sedatives as coping mechanisms, and maintain open communication with trusted healthcare providers."

    return {
        'recommendation_title': title,
        'recommendation_summary': summary,
        'physician_summary': physician_summary,
        'daily_schedule': daily_schedule,
        'weekly_activities': weekly_activities,
        'coping_strategies': coping_strategies,
        'preventive_strategies': preventive_strategies,
        'lifestyle_modifications': lifestyle_modifications,
        'follow_up_guidance': "Follow-up clinical consultation within 7-14 days recommended.",
        'frequently_reported_symptoms': freq_symptoms[:8],
        'identified_patterns': f"Reported patterns concentrated in {', '.join(elevated_names) if elevated_names else 'general wellness spheres'}.",
        'daily_activity_effects': "Reported interference with daily concentration, task completion, and energy restoration.",
        'areas_for_investigation': f"Physician inquiry into onset duration, psychosocial stressors, and sleep quality related to {', '.join(elevated_names) if elevated_names else 'wellness domains'}."
    }


def _call_gemini_api(assessment, patient, elevated_categories, freq_symptoms, pathway):
    """
    Calls Google Gemini API using structured JSON output mode.
    """
    api_key = settings.GEMINI_API_KEY
    model = settings.GEMINI_MODEL_NAME
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    prompt_content = f"""
    Analyze the following de-identified patient mental health screening:
    - Age: {patient.age or 25}
    - Routine/Work schedule: {patient.work_or_school_schedule}
    - Personal interests: {patient.personal_interests}
    - Pathway: {pathway}
    - PHQ-9 Depression Score: {assessment.phq9_score}
    - GAD-7 Anxiety Score: {assessment.gad7_score}
    - Elevated Categories: {json.dumps(elevated_categories)}
    - Frequently Reported Symptoms: {json.dumps(freq_symptoms[:10])}
    - Safety Concern Flag: {assessment.has_safety_flag}

    Return a JSON object with the following keys:
    - recommendation_title: string
    - recommendation_summary: string
    - physician_summary: string
    - daily_schedule: list of objects with time, activity, description, category, purpose
    - weekly_activities: list of objects with activity, description, purpose
    - coping_strategies: list of strings
    - preventive_strategies: list of strings
    - lifestyle_modifications: string
    - follow_up_guidance: string
    - identified_patterns: string
    - daily_activity_effects: string
    - areas_for_investigation: string
    """

    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT},
                    {"text": prompt_content}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2
        }
    }

    response = requests.post(url, headers=headers, json=payload, timeout=12)
    if response.status_code == 200:
        res_json = response.json()
        raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
        return json.loads(raw_text)
    else:
        logger.error(f"Gemini API returned status {response.status_code}: {response.text}")
        return None
