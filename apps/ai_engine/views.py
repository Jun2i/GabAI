import json
import logging
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from apps.safety.models import SafetyAssessment

logger = logging.getLogger(__name__)

CRISIS_PATTERNS = [
    r'\bsuicid(e|al|ality)?\b',
    r'\b(kill|killing)\s+(myself|oneself)\b',
    r'\b(end|ending)\s+my\s+life\b',
    r'\bwant\s+to\s+die\b',
    r'\b(hurt|hurting|harm|harming)\s+(myself|oneself)\b',
    r'\b(cut|cutting)\s+(my\s+wrists|myself)\b',
    r'\boverdose\b',
    r'\b(take|taking)\s+my\s+life\b',
    r'\b(hang|hanging)\s+myself\b',
    r'\bno\s+reason\s+to\s+live\b',
    r'\bbetter\s+off\s+dead\b',
]

def check_crisis_intent(text):
    text_lower = text.lower()
    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False

def get_crisis_response():
    return (
        "⚠️ **Immediate Crisis & Safety Support**\n\n"
        "If you are feeling overwhelmed, hopeless, or having thoughts of hurting yourself, "
        "please know that **you are not alone and support is available right now**.\n\n"
        "📞 **National Mental Health Crisis Hotline**: **1553** (24/7 Toll-Free)\n"
        "📱 **Hopeline Philippines**: 0917-558-4673 / (02) 8804-4673\n"
        "💬 **In Touch Community Services**: 0917-800-1123\n\n"
        "👉 You can also open our [Emergency Crisis Resources Hub](/safety/crisis/) "
        "for immediate escalation to our clinical team and local emergency assistance."
    )

def generate_heuristic_chat_response(message, user):
    """
    Intelligent, empathetic, non-diagnostic response engine.
    Complies with clinical decision support boundaries.
    """
    msg = message.lower().strip()

    # Greetings
    if re.search(r'\b(hi|hello|hey|good morning|good afternoon|good evening|greetings)\b', msg) and not any(k in msg for k in ['breath', 'anxious', 'stress', 'depress', 'sleep', 'focus']):
        name = user.first_name if (user and user.is_authenticated and user.first_name) else "there"
        return (
            f"Hello {name}! 👋 I am your GabAI Wellness Assistant.\n\n"
            "I'm here to provide supportive mental wellness guidance, guide you through coping exercises, "
            "explain our 13-category screening process, or help you connect with our medical staff.\n\n"
            "How can I support you today?"
        )

    # Breathing / Grounding
    if any(k in msg for k in ['breath', 'breathing', 'grounding', 'relax', 'calm down', 'panic', 'heart racing']):
        return (
            "🧘 **Guided 4-7-8 Relaxing Breath Technique**\n\n"
            "Let's take a moment together to calm your autonomic nervous system:\n\n"
            "1. **Inhale quietly** through your nose for **4 seconds**.\n"
            "2. **Hold your breath** gently for **7 seconds**.\n"
            "3. **Exhale completely** through your mouth making a gentle whoosh sound for **8 seconds**.\n"
            "4. Repeat this cycle 3 to 4 times.\n\n"
            "💡 *Tip:* You can also try the **5-4-3-2-1 Sensory Grounding** method: Notice 5 things you can see, "
            "4 you can physically feel, 3 you can hear, 2 you can smell, and 1 positive affirmation."
        )

    # Anxiety / Overwhelm / Stress
    if any(k in msg for k in ['anxious', 'anxiety', 'worried', 'stress', 'stressed', 'overwhelmed', 'burnout']):
        return (
            "🌿 **Managing Stress & Elevated Anxiety**\n\n"
            "It is completely valid to feel stressed or anxious when juggling life demands. Here are evidence-based steps to ease the load:\n\n"
            "• **Ground Yourself:** Take 5 deep, slow abdominal breaths.\n"
            "• **Brain Dump:** Write down everything currently on your mind without judgment, then circle just ONE item you can influence right now.\n"
            "• **Sensory Reset:** Step outside for 5 minutes of natural sunlight or wash your hands with cool water.\n"
            "• **Clinical Screening:** If anxiety has persisted for several days, consider completing our [13-Category Screening](/assessments/intro/) "
            "so our physicians can evaluate your symptom patterns and authorize a personalized coping plan."
        )

    # Depression / Sadness / Motivation / Hopeless
    if any(k in msg for k in ['sad', 'depressed', 'depression', 'unmotivated', 'empty', 'lonely', 'exhausted']):
        return (
            "💙 **Supportive Guidance for Low Mood**\n\n"
            "Experiencing persistent fatigue or low mood can make even small daily tasks feel monumental. Please be gentle with yourself:\n\n"
            "• **Micro-Goals:** Focus on tiny, achievable actions (e.g., drink a glass of water, open your window for fresh air).\n"
            "• **Gentle Movement:** A brief 5-minute stroll or gentle stretching helps stimulate mood-regulating neurochemicals.\n"
            "• **Reach Out:** Connect with a trusted friend, family member, or healthcare provider.\n\n"
            "⚠️ *Reminder:* GabAI recommendations are reviewed by licensed physicians to ensure you receive safe, human-supervised clinical guidance. "
            "You can book a consultation directly through [Appointments](/appointments/request/)."
        )

    # Sleep issues
    if any(k in msg for k in ['sleep', 'insomnia', 'cant sleep', "can't sleep", 'tired', 'nightmare', 'awake']):
        return (
            "🌙 **Sleep Hygiene & Circadian Stabilization**\n\n"
            "Healthy sleep is foundational to emotional resilience. Consider these evidence-based habits:\n\n"
            "• **The 10-3-2-1 Rule:**\n"
            "  - 10 hours before bed: No more caffeine.\n"
            "  - 3 hours before bed: No heavy meals or vigorous exercise.\n"
            "  - 2 hours before bed: Wind down work or intensive mental tasks.\n"
            "  - 1 hour before bed: Turn off screens (blue light disrupts melatonin).\n"
            "• **Consistent Schedule:** Wake up and go to sleep at the exact same hour every day, even on weekends.\n"
            "• **Wind-Down Routine:** Try light reading, herbal tea (chamomile), or gentle stretching."
        )

    # ADHD / Focus / Procrastination
    if any(k in msg for k in ['focus', 'adhd', 'distracted', 'procrastinat', 'attention', 'cant concentrate']):
        return (
            "🎯 **Executive Function & Focus Strategies**\n\n"
            "If you struggle with maintaining attention or starting tasks:\n\n"
            "• **The 25/5 Pomodoro Method:** Work for 25 minutes on a single task with all notifications muted, followed by a mandatory 5-minute break.\n"
            "• **Task Breakdown:** Deconstruct large intimidating tasks into physical micro-steps (e.g. 'open laptop', 'create document').\n"
            "• **Visual Cues:** Keep sticky notes or a checklist in plain view on your desk.\n"
            "• Check out your [Personalized Daily Schedule](/wellness/schedule/) for structured routine blocks."
        )

    # Screening / Questionnaire
    if any(k in msg for k in ['screening', 'questionnaire', 'assessment', 'test', 'phq', 'gad']):
        return (
            "📋 **About GabAI 13-Category Screening**\n\n"
            "Our comprehensive screening questionnaire covers 13 core psychological domains:\n"
            "1. Anxiety (GAD-7 standard scale)\n"
            "2. Depression (PHQ-9 standard scale)\n"
            "3. Stress & Burnout\n"
            "4. ADHD Symptoms\n"
            "5. Bipolar-related traits\n"
            "6. OCD Indicators\n"
            "7. PTSD & Trauma\n"
            "8. Autism Developmental Traits\n"
            "9. Sleep Quality\n"
            "10. Eating Habits\n"
            "11. Psychosis-related Experiences\n"
            "12. Substance Use\n"
            "13. Personal Safety (Critical Protocol)\n\n"
            "👉 Ready to begin? Go to [Take Clinical Assessment](/assessments/intro/)."
        )

    # Physician approval / AI guardrails
    if any(k in msg for k in ['doctor', 'physician', 'approve', 'approval', 'safe', 'diagnosis', 'prescribe']):
        return (
            "🩺 **Physician Supervision & AI Ethical Guardrails**\n\n"
            "At GabAI, **Artificial Intelligence NEVER independently diagnoses or releases clinical advice**.\n\n"
            "• Every AI recommendation is initially marked **PENDING PHYSICIAN APPROVAL**.\n"
            "• A board-certified physician examines your screening responses, verifies clinical indicators, and can **Approve**, **Modify**, or **Hold** recommendations.\n"
            "• Only verified recommendations become visible on your patient dashboard to guarantee absolute medical safety."
        )

    # Daily Wellness Schedule / Habits
    if any(k in msg for k in ['schedule', 'routine', 'wellness', 'habit', 'activity', 'tracker']):
        return (
            "📅 **Daily Wellness Schedules & Habit Tracking**\n\n"
            "GabAI builds tailored daily timelines with morning, afternoon, and evening routines based on your assessment results:\n\n"
            "• Track daily completion percentage with real-time progress charts.\n"
            "• Maintain daily habit streaks (7-day and 14-day resilience milestones).\n"
            "• Mark activities as **Completed**, **Skipped**, or **Rescheduled**.\n\n"
            "👉 Open your [Daily Wellness Schedule](/wellness/schedule/) to track today's activities!"
        )

    # Appointment / Doctor consultation
    if any(k in msg for k in ['appointment', 'consult', 'booking', 'meet doctor', 'psychiatrist']):
        return (
            "🗓️ **Booking a Physician Consultation**\n\n"
            "You can easily connect with a qualified psychiatrist or clinical psychologist through GabAI:\n\n"
            "• **Options:** Telehealth Video Consultation or In-Person Clinic Visit.\n"
            "• **Reason:** Diagnostic evaluation, recommendation review, or therapy referral.\n\n"
            "👉 Schedule your session here: [Request Appointment](/appointments/request/)."
        )

    # Default fallback
    return (
        "Thank you for sharing that with me. As your GabAI Wellness Assistant, "
        "I am here to support your mental health journey with evidence-based wellness techniques and navigation.\n\n"
        "Here are a few things you can ask me about:\n"
        "• *'Can you guide me through a calming breathing exercise?'*\n"
        "• *'How does the 13-category screening assessment work?'*\n"
        "• *'What is the 10-3-2-1 sleep hygiene rule?'*\n"
        "• *'How do doctors approve my recommendations?'*\n"
        "• *'How do I book an appointment with a psychiatrist?'*\n\n"
        "*(Note: GabAI provides wellness decision support, not medical diagnosis. In a crisis, dial 1553).* "
    )


@csrf_exempt
@require_POST
def chat_api_view(request):
    """
    AJAX endpoint for the floating AI Chatbot widget.
    Processes user queries with clinical guardrails, crisis checks, and Gemini API / fallback.
    """
    try:
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode('utf-8'))
            user_message = data.get('message', '').strip()
        else:
            user_message = request.POST.get('message', '').strip()
    except Exception as e:
        logger.error(f"Chat payload parsing error: {e}")
        return JsonResponse({'status': 'error', 'message': 'Invalid request format.'}, status=400)

    if not user_message:
        return JsonResponse({'status': 'error', 'message': 'Empty message received.'}, status=400)

    # 1. IMMEDIATE CRISIS DETECTION (Category 13 Safety Protocol)
    if check_crisis_intent(user_message):
        # If user is authenticated patient, record an internal safety flag if applicable
        if request.user.is_authenticated and request.user.is_patient:
            try:
                patient = request.user.patient_profile
                latest_assessment = patient.assessments.last()
                SafetyAssessment.objects.create(
                    patient=patient,
                    assessment=latest_assessment,
                    has_suicidal_ideation=True,
                    has_self_harm_intent=True,
                    escalation_level='EMERGENCY',
                    emergency_contacts_contacted=False,
                    clinical_action_notes="Triggered via AI Chatbot crisis keyword detection."
                )
            except Exception as ex:
                logger.error(f"Failed to record chatbot safety assessment: {ex}")

        return JsonResponse({
            'status': 'success',
            'reply': get_crisis_response(),
            'is_crisis': True
        })

    # 2. ATTEMPT GEMINI LLM CALL IF CONFIGURED
    reply = None
    if getattr(settings, 'GEMINI_API_KEY', None):
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')

            system_context = (
                "You are the GabAI Clinical Assistant & Wellness Companion. "
                "You provide supportive, empathetic, evidence-based mental wellness guidance, "
                "coping exercises (breathing, sleep hygiene, grounding), and help users navigate "
                "the GabAI healthcare platform.\n\n"
                "CRITICAL CLINICAL GUARDRAILS:\n"
                "1. NEVER give a medical diagnosis or diagnose any disorder.\n"
                "2. NEVER prescribe medication or dosage recommendations.\n"
                "3. Always emphasize that recommendations are supportive wellness tools, reviewed by physicians.\n"
                "4. Keep responses concise, warm, formatted with clear markdown bullet points, easy to read in a chat widget.\n"
                "5. If user expresses crisis, refer to Philippine DOH Hotline 1553 and Hopeline 0917-558-4673."
            )

            prompt = f"{system_context}\n\nUser Question: {user_message}\n\nAssistant Response:"
            response = model.generate_content(prompt)
            if response and response.text:
                reply = response.text.strip()
        except Exception as e:
            logger.warning(f"Gemini chat API fallback to heuristic: {e}")
            reply = None

    # 3. CLINICAL HEURISTIC FALLBACK
    if not reply:
        reply = generate_heuristic_chat_response(user_message, request.user)

    return JsonResponse({
        'status': 'success',
        'reply': reply,
        'is_crisis': False
    })
