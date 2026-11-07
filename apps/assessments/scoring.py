from .models import QuestionnaireCategory, Question, PatientResponse, ScreeningResult
from apps.safety.models import SafetyAssessment
from apps.notifications.models import Notification
from apps.accounts.models import AuditLog, User
from django.utils import timezone

def calculate_assessment_scores(assessment):
    """
    Calculates category scores, standard scales (PHQ-9, GAD-7),
    evaluates safety triggers, and creates screening results.
    """
    responses = PatientResponse.objects.filter(assessment=assessment).select_related('question__category')
    categories = QuestionnaireCategory.objects.all().order_by('category_order')

    total_questions = Question.objects.count()
    answered_count = responses.count()
    assessment.total_questions_answered = answered_count
    assessment.completion_rate = (answered_count / total_questions * 100.0) if total_questions > 0 else 0.0

    phq9_total = 0
    phq9_count = 0
    gad7_total = 0
    gad7_count = 0
    stress_total = 0

    safety_triggered = False
    safety_triggers_list = []

    for category in categories:
        cat_responses = [r for r in responses if r.question.category_id == category.id]
        cat_questions = Question.objects.filter(category=category)
        
        raw_score = sum(r.numeric_score for r in cat_responses)
        # Calculate max possible score for answered questions or total category questions
        if category.is_developmental:
            max_score = len(cat_questions) * 1.0
        else:
            max_score = len(cat_questions) * 3.0

        score_pct = (raw_score / max_score * 100.0) if max_score > 0 else 0.0

        # Determine category severity level
        if score_pct >= 75.0:
            severity = 'HIGH'
            is_elevated = True
        elif score_pct >= 50.0:
            severity = 'ELEVATED'
            is_elevated = True
        elif score_pct >= 30.0:
            severity = 'MODERATE'
            is_elevated = True
        elif score_pct >= 15.0:
            severity = 'MILD'
            is_elevated = False
        else:
            severity = 'MINIMAL'
            is_elevated = False

        # Specific scale accumulations
        if category.code == 'DEPRESSION':
            phq9_total = int(raw_score)
            phq9_count = len(cat_responses)
        elif category.code == 'ANXIETY':
            gad7_total = int(raw_score)
            gad7_count = len(cat_responses)
        elif category.code == 'STRESS':
            stress_total = int(raw_score)

        # Check Category 13 and critical safety questions
        for r in cat_responses:
            if r.question.is_critical_safety or category.code == 'SAFETY':
                # Positive answer indicating risk:
                # For frequency: > 0 ("Several days", "More than half", "Nearly every day")
                # For yes/no: "Yes" or value == "1"
                val = str(r.response_value).strip().lower()
                if (r.numeric_score > 0 and val not in ['0', 'no', 'prefer not to answer']) or val in ['yes', '1', '2', '3']:
                    safety_triggered = True
                    safety_triggers_list.append(f"{r.question.question_text}: {r.response_label}")

        # Update or create ScreeningResult record
        ScreeningResult.objects.update_or_create(
            assessment=assessment,
            category=category,
            defaults={
                'raw_score': round(raw_score, 2),
                'max_score': round(max_score, 2),
                'score_percentage': round(score_pct, 1),
                'severity_level': severity,
                'is_elevated': is_elevated,
                'indicator_summary': f"Reported score {raw_score:.1f}/{max_score:.1f} ({score_pct:.1f}%). Indicator: {severity}."
            }
        )

    # Depression indicator interpretation (scaled for full or streamlined questionnaire)
    assessment.phq9_score = phq9_total
    if phq9_count <= 4:
        # Streamlined 3-question scale (0-9)
        if phq9_total >= 7:
            assessment.phq9_severity = "Elevated Depressive Indicators"
        elif phq9_total >= 5:
            assessment.phq9_severity = "Moderate Depressive Indicators"
        elif phq9_total >= 3:
            assessment.phq9_severity = "Mild Depressive Indicators"
        else:
            assessment.phq9_severity = "Minimal / No Depressive Indicators"
    else:
        # Standard 9-item PHQ-9 scale (0-27)
        if phq9_total >= 20:
            assessment.phq9_severity = "Severe Depression Symptoms"
        elif phq9_total >= 15:
            assessment.phq9_severity = "Moderately Severe Depression Symptoms"
        elif phq9_total >= 10:
            assessment.phq9_severity = "Moderate Depression Symptoms"
        elif phq9_total >= 5:
            assessment.phq9_severity = "Mild Depression Symptoms"
        else:
            assessment.phq9_severity = "Minimal / No Depression Symptoms"

    # Anxiety indicator interpretation (scaled for full or streamlined questionnaire)
    assessment.gad7_score = gad7_total
    if gad7_count <= 4:
        # Streamlined 3-question scale (0-9)
        if gad7_total >= 7:
            assessment.gad7_severity = "Elevated Anxiety Indicators"
        elif gad7_total >= 5:
            assessment.gad7_severity = "Moderate Anxiety Indicators"
        elif gad7_total >= 3:
            assessment.gad7_severity = "Mild Anxiety Indicators"
        else:
            assessment.gad7_severity = "Minimal / No Anxiety Indicators"
    else:
        # Standard 7-item GAD-7 scale (0-21)
        if gad7_total >= 15:
            assessment.gad7_severity = "Severe Anxiety Symptoms"
        elif gad7_total >= 10:
            assessment.gad7_severity = "Moderate Anxiety Symptoms"
        elif gad7_total >= 5:
            assessment.gad7_severity = "Mild Anxiety Symptoms"
        else:
            assessment.gad7_severity = "Minimal / No Anxiety Symptoms"

    assessment.stress_score = stress_total
    assessment.has_safety_flag = safety_triggered
    assessment.save()

    # If Safety is triggered: Execute immediate emergency workflow
    if safety_triggered:
        trigger_immediate_safety_protocol(assessment, safety_triggers_list)

    return assessment


def trigger_immediate_safety_protocol(assessment, triggers_list):
    """
    EMERGENCY WORKFLOW:
    - Never wait for ordinary AI analysis or physician approval.
    - Create SafetyAssessment record immediately.
    - Set patient flag has_active_safety_alert = True.
    - Notify clinical team / assigned physician immediately.
    - Log emergency audit entry.
    """
    patient = assessment.patient
    patient.has_active_safety_alert = True
    patient.save(update_fields=['has_active_safety_alert'])

    trigger_details = "\n".join(triggers_list) if triggers_list else "Positive responses to safety/crisis screening items."
    
    safety_record, created = SafetyAssessment.objects.update_or_create(
        assessment=assessment,
        patient=patient,
        defaults={
            'intent_reported': True,
            'plan_reported': any('plan' in t.lower() for t in triggers_list),
            'inability_to_stay_safe': any('stay safe' in t.lower() or 'control' in t.lower() for t in triggers_list),
            'immediate_danger': True,
            'urgency_level': 'CRITICAL',
            'status': 'ACTIVE_EMERGENCY',
            'safety_triggers_detected': trigger_details,
            'escalated_to': patient.assigned_physician,
            'escalated_at': timezone.now()
        }
    )

    # Urgent notifications to physicians and clinical staff
    recipients = User.objects.filter(role__in=[User.Role.PHYSICIAN, User.Role.STAFF, User.Role.ADMIN])
    for recipient in recipients:
        Notification.send(
            recipient=recipient,
            notification_type='SAFETY_ALERT',
            title=f"URGENT SAFETY ALERT: Patient {patient.user.get_full_name()}",
            message=f"Patient {patient.user.get_full_name()} (ID #{patient.id}) reported active crisis or safety concerns during Assessment #{assessment.id}. Immediate clinical response required.",
            action_url=f"/safety/emergency/{safety_record.id}/",
            is_urgent=True
        )

    # Log to audit log
    AuditLog.objects.create(
        user=patient.user,
        action='SAFETY_ALERT_TRIGGERED',
        entity_name='SafetyAssessment',
        entity_id=str(safety_record.id),
        details=f"Urgent safety protocol activated. Triggers:\n{trigger_details}"
    )

