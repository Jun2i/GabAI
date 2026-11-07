from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import QuestionnaireCategory, Question, Assessment, PatientResponse, ScreeningResult
from .scoring import calculate_assessment_scores
from apps.ai_engine.gemini_service import generate_ai_analysis_and_recommendations
from apps.accounts.decorators import patient_required, staff_or_physician_required
from apps.patients.models import PatientProfile
from apps.accounts.models import AuditLog

@login_required
def assessment_intro_view(request):
    """
    Assessment welcome & clinical disclaimer screen before starting.
    Explains the 13 categories, confidentiality under RA 10173, and non-diagnostic nature.
    """
    categories = QuestionnaireCategory.objects.all().order_by('category_order')
    patient_profile = getattr(request.user, 'patient_profile', None)

    latest_assessment = None
    if patient_profile:
        latest_assessment = Assessment.objects.filter(patient=patient_profile).order_by('-created_at').first()

    context = {
        'categories': categories,
        'latest_assessment': latest_assessment,
    }
    return render(request, 'assessments/intro.html', context)


@login_required
@patient_required
def start_assessment_view(request):
    """
    Creates a new Assessment instance and directs the patient to the interactive form.
    """
    patient = request.user.patient_profile
    assessment = Assessment.objects.create(
        patient=patient,
        status='IN_PROGRESS',
        disclaimer_accepted=True
    )
    AuditLog.objects.create(
        user=request.user,
        action='ASSESSMENT_SUBMITTED',
        entity_name='Assessment',
        entity_id=str(assessment.id),
        details="Patient initiated new 13-category screening assessment."
    )
    return redirect('assessments:take_assessment', assessment_id=assessment.id)


@login_required
def take_assessment_view(request, assessment_id):
    """
    Interactive 13-category assessment questionnaire.
    Renders all questions organized by category with frequency and developmental response options.
    """
    assessment = get_object_or_404(Assessment, id=assessment_id)
    
    # Permission verification
    if request.user.is_patient and assessment.patient.user != request.user:
        messages.error(request, "Access unauthorized.")
        return redirect('patients:dashboard')

    categories = QuestionnaireCategory.objects.prefetch_related('questions').order_by('category_order')

    if request.method == 'POST':
        # Process questionnaire submission
        for cat in categories:
            for q in cat.questions.all():
                field_name = f"question_{q.id}"
                val = request.POST.get(field_name)

                if val is not None:
                    # Calculate numeric score based on question type
                    numeric_val = 0.0
                    label = ""

                    if q.question_type == 'FREQUENCY':
                        val_int = int(val)
                        labels = {0: 'Not at all', 1: 'Several days', 2: 'More than half the days', 3: 'Nearly every day'}
                        numeric_val = float(val_int)
                        label = labels.get(val_int, str(val))
                    elif q.question_type == 'DEVELOPMENTAL':
                        dev_scores = {'Yes': 1.0, 'No': 0.0, 'Unsure': 0.5, 'Prefer not to answer': 0.0}
                        numeric_val = dev_scores.get(val, 0.0)
                        label = val
                    else: # YES_NO
                        numeric_val = 1.0 if val in ['Yes', '1'] else 0.0
                        label = 'Yes' if numeric_val == 1.0 else 'No'

                    PatientResponse.objects.update_or_create(
                        assessment=assessment,
                        question=q,
                        defaults={
                            'response_value': str(val),
                            'numeric_score': numeric_val,
                            'response_label': label
                        }
                    )

        assessment.status = 'SUBMITTED'
        assessment.submitted_at = timezone.now()
        assessment.save()

        # 1. Calculate scores, PHQ-9, GAD-7, and evaluate Category 13 safety triggers
        calculate_assessment_scores(assessment)

        # 2. Trigger AI Analysis and Recommendation Generation
        generate_ai_analysis_and_recommendations(assessment)

        # 3. If safety flag was raised, redirect to crisis support view
        if assessment.has_safety_flag:
            messages.warning(
                request,
                "Immediate safety indicators were noted. A clinical support specialist has been alerted. Please view the crisis resources below."
            )
            return redirect('safety:crisis_resources')

        messages.success(request, "Assessment submitted successfully! AI analysis is complete and has been forwarded to a physician for clinical review.")
        return redirect('assessments:summary', assessment_id=assessment.id)

    # Preload existing answers if resuming
    existing_responses = {r.question_id: r.response_value for r in assessment.responses.all()}
    total_questions = sum(c.questions.count() for c in categories)

    context = {
        'assessment': assessment,
        'categories': categories,
        'existing_responses': existing_responses,
        'total_questions': total_questions,
    }
    return render(request, 'assessments/questionnaire_form.html', context)


@login_required
def assessment_summary_view(request, assessment_id):
    """
    Shows submitted assessment results, category score indicators,
    and status of physician review. Enforces clear non-diagnostic disclaimers.
    """
    assessment = get_object_or_404(
        Assessment.objects.select_related('patient__user'),
        id=assessment_id
    )

    if request.user.is_patient and assessment.patient.user != request.user:
        messages.error(request, "Access unauthorized.")
        return redirect('patients:dashboard')

    results = assessment.screening_results.select_related('category').order_by('category__category_order')
    recommendation = assessment.ai_recommendations.first()
    ai_analysis = getattr(assessment, 'ai_analysis', None)

    context = {
        'assessment': assessment,
        'results': results,
        'recommendation': recommendation,
        'ai_analysis': ai_analysis,
        'is_physician': request.user.is_physician or request.user.is_healthcare_staff,
    }
    return render(request, 'assessments/summary.html', context)


@login_required
def assessment_history_view(request):
    """
    Displays assessment history with screening trends over time (10 per page).
    """
    patient = None
    if request.user.is_patient:
        patient = request.user.patient_profile
        assessments_qs = Assessment.objects.filter(patient=patient).order_by('-created_at')
    else:
        patient_id = request.GET.get('patient_id')
        if patient_id:
            patient = get_object_or_404(PatientProfile, id=patient_id)
            assessments_qs = Assessment.objects.filter(patient=patient).order_by('-created_at')
        else:
            assessments_qs = Assessment.objects.all().order_by('-created_at')

    page_number = request.GET.get('page', 1)
    paginator = Paginator(assessments_qs, 10)
    try:
        assessments_page = paginator.page(page_number)
    except PageNotAnInteger:
        assessments_page = paginator.page(1)
    except EmptyPage:
        assessments_page = paginator.page(paginator.num_pages)

    context = {
        'assessments': assessments_page,
        'paginator': paginator,
        'page_obj': assessments_page,
        'patient': patient,
    }
    return render(request, 'assessments/history.html', context)

