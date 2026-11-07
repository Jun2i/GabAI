from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Count
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import PhysicianProfile, ClinicalRecord, FollowUp, HealthcareStaff
from apps.patients.models import PatientProfile
from apps.assessments.models import Assessment, ScreeningResult, QuestionnaireCategory
from apps.recommendations.models import AiRecommendation
from apps.safety.models import SafetyAssessment
from apps.appointments.models import Appointment
from apps.accounts.decorators import staff_or_physician_required, physician_required
from apps.accounts.models import AuditLog
from datetime import date, timedelta

@login_required
@staff_or_physician_required
def physician_dashboard_view(request):
    """
    Professional Physician & Psychiatrist Clinical Dashboard.
    Provides KPIs, triage alerts, multi-parameter filtering, paginated data table,
    and direct links to approval workflows.
    """
    # KPI Metrics
    total_patients = PatientProfile.objects.count()
    assessments_awaiting = Assessment.objects.filter(status__in=['SUBMITTED', 'ANALYZED']).count()
    recommendations_awaiting = AiRecommendation.objects.filter(status='PENDING_APPROVAL').count()
    safety_alerts_active = SafetyAssessment.objects.filter(status__in=['ACTIVE_EMERGENCY', 'UNDER_CLINICAL_REVIEW']).count()
    upcoming_appointments = Appointment.objects.filter(
        appointment_date__gte=date.today(),
        status__in=['REQUESTED', 'CONFIRMED']
    ).count()
    completed_evaluations = ClinicalRecord.objects.count()
    follow_up_cases = FollowUp.objects.filter(status='SCHEDULED').count()

    # Filters
    date_filter = request.GET.get('date')
    status_filter = request.GET.get('status')
    search_query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category')
    physician_filter = request.GET.get('physician')
    page_number = request.GET.get('page', 1)

    recs_qs = AiRecommendation.objects.select_related(
        'patient__user', 'assessment', 'approved_by__user'
    ).order_by('-created_at')

    if status_filter:
        recs_qs = recs_qs.filter(status=status_filter)
    if search_query:
        recs_qs = recs_qs.filter(
            Q(patient__user__first_name__icontains=search_query) |
            Q(patient__user__last_name__icontains=search_query) |
            Q(patient__user__username__icontains=search_query) |
            Q(patient__id__icontains=search_query)
        )
    if date_filter:
        recs_qs = recs_qs.filter(created_at__date=date_filter)
    if physician_filter:
        recs_qs = recs_qs.filter(patient__assigned_physician_id=physician_filter)

    # Attach computed indicator levels and results to records
    for rec in recs_qs:
        ass = rec.assessment
        if ass and ass.has_safety_flag:
            rec.risk_code = 'CRITICAL'
            rec.risk_badge_class = 'bg-danger text-white'
            rec.risk_label = 'Critical Safety Flag'
            rec.assessment_result_summary = 'Crisis Indicator • Self-Harm Concern'
        elif rec.pathway == 'PATHWAY_B':
            if (ass and ass.phq9_score and ass.phq9_score >= 7) or (ass and ass.gad7_score and ass.gad7_score >= 7):
                rec.risk_code = 'HIGH'
                rec.risk_badge_class = 'bg-danger-subtle text-danger border border-danger'
                rec.risk_label = 'High Risk'
            else:
                rec.risk_code = 'MODERATE'
                rec.risk_badge_class = 'bg-warning-subtle text-warning-emphasis border border-warning-subtle'
                rec.risk_label = 'Moderate Risk'
            
            gad_text = ass.gad7_severity if (ass and ass.gad7_severity) else 'Elevated Anxiety'
            phq_text = ass.phq9_severity if (ass and ass.phq9_severity) else 'Elevated Depressive'
            rec.assessment_result_summary = f"{gad_text} / {phq_text}"
        else:
            if (ass and ass.stress_score and ass.stress_score >= 3) or (ass and ass.gad7_score and ass.gad7_score >= 3):
                rec.risk_code = 'MILD'
                rec.risk_badge_class = 'bg-info-subtle text-info-emphasis border border-info-subtle'
                rec.risk_label = 'Mild Indicator'
                rec.assessment_result_summary = 'Mild Situational Stress • Good Coping'
            else:
                rec.risk_code = 'LOW'
                rec.risk_badge_class = 'bg-success-subtle text-success border border-success-subtle'
                rec.risk_label = 'Low Risk'
                rec.assessment_result_summary = 'Minimal Indicators • Resilient Baseline'

    # Paginate: 10 records per page (clean, non-overcrowded table)
    paginator = Paginator(recs_qs, 10)
    try:
        recommendations_page = paginator.page(page_number)
    except PageNotAnInteger:
        recommendations_page = paginator.page(1)
    except EmptyPage:
        recommendations_page = paginator.page(paginator.num_pages)

    categories = QuestionnaireCategory.objects.all().order_by('category_order')
    physicians = PhysicianProfile.objects.select_related('user').all()

    # Recent assessments awaiting action
    recent_assessments = Assessment.objects.select_related(
        'patient__user'
    ).order_by('-created_at')[:10]

    # Active safety alerts
    urgent_safety_cases = SafetyAssessment.objects.filter(
        status__in=['ACTIVE_EMERGENCY', 'UNDER_CLINICAL_REVIEW']
    ).select_related('patient__user')[:5]

    context = {
        'total_patients': total_patients,
        'assessments_awaiting': assessments_awaiting,
        'recommendations_awaiting': recommendations_awaiting,
        'safety_alerts_active': safety_alerts_active,
        'upcoming_appointments': upcoming_appointments,
        'completed_evaluations': completed_evaluations,
        'follow_up_cases': follow_up_cases,
        'recommendations': recommendations_page,
        'page_obj': recommendations_page,
        'paginator': paginator,
        'total_records_count': recs_qs.count(),
        'recent_assessments': recent_assessments,
        'urgent_safety_cases': urgent_safety_cases,
        'categories': categories,
        'physicians': physicians,
        'current_filters': {
            'status': status_filter,
            'q': search_query,
            'date': date_filter,
            'category': category_filter,
            'physician': physician_filter,
        }
    }
    return render(request, 'physicians/dashboard.html', context)


@login_required
@staff_or_physician_required
def patient_clinical_detail_view(request, patient_id):
    """
    Comprehensive Medical Chart for a Patient.
    Displays screening responses, AI analysis summaries, recommendations,
    and physician-confirmed clinical findings and diagnoses.
    """
    patient = get_object_or_404(
        PatientProfile.objects.select_related('user', 'assigned_physician__user'),
        id=patient_id
    )
    assessments = Assessment.objects.filter(patient=patient).order_by('-created_at')
    recommendations = AiRecommendation.objects.filter(patient=patient).order_by('-created_at')
    clinical_records = ClinicalRecord.objects.filter(patient=patient).select_related('physician__user').order_by('-created_at')
    follow_ups = FollowUp.objects.filter(patient=patient).select_related('physician__user').order_by('scheduled_date')
    safety_history = SafetyAssessment.objects.filter(patient=patient).order_by('-created_at')
    latest_assessment = assessments.first()

    context = {
        'patient': patient,
        'assessments': assessments,
        'recommendations': recommendations,
        'clinical_records': clinical_records,
        'follow_ups': follow_ups,
        'safety_history': safety_history,
        'latest_assessment': latest_assessment,
    }
    return render(request, 'physicians/patient_detail.html', context)


@login_required
@physician_required
def add_clinical_record_view(request, patient_id):
    """
    Physician documents formal clinical evaluation, diagnosis,
    treatment plan, and clinical findings.
    """
    patient = get_object_or_404(PatientProfile, id=patient_id)
    physician = get_object_or_404(PhysicianProfile, user=request.user)

    if request.method == 'POST':
        findings = request.POST.get('clinical_findings', '').strip()
        diagnosis = request.POST.get('clinical_diagnosis', '').strip()
        treatment = request.POST.get('treatment_plan', '').strip()
        follow_up_notes = request.POST.get('follow_up_instructions', '').strip()
        confidential = request.POST.get('confidential_notes', '').strip()
        assessment_id = request.POST.get('assessment_id')

        assessment = Assessment.objects.filter(id=assessment_id).first() if assessment_id else None

        if not findings:
            messages.error(request, "Clinical findings description is required.")
            return redirect('physicians:patient_detail', patient_id=patient.id)

        record = ClinicalRecord.objects.create(
            patient=patient,
            physician=physician,
            assessment=assessment,
            clinical_findings=findings,
            clinical_diagnosis=diagnosis,
            treatment_plan=treatment,
            follow_up_instructions=follow_up_notes,
            confidential_notes=confidential
        )

        AuditLog.objects.create(
            user=request.user,
            action='CLINICAL_NOTE_ADDED',
            entity_name='ClinicalRecord',
            entity_id=str(record.id),
            details=f"Physician recorded clinical evaluation for patient {patient.user.get_full_name()}."
        )

        messages.success(request, f"Clinical record documented for {patient.user.get_full_name()}.")
        return redirect('physicians:patient_detail', patient_id=patient.id)

    assessments = Assessment.objects.filter(patient=patient).order_by('-created_at')
    context = {
        'patient': patient,
        'assessments': assessments,
    }
    return render(request, 'physicians/add_clinical_record.html', context)


@login_required
@physician_required
def schedule_follow_up_view(request, patient_id):
    """
    Schedules a clinical follow-up for the patient.
    """
    patient = get_object_or_404(PatientProfile, id=patient_id)
    physician = get_object_or_404(PhysicianProfile, user=request.user)

    if request.method == 'POST':
        sched_date = request.POST.get('scheduled_date')
        sched_time = request.POST.get('scheduled_time')
        notes = request.POST.get('notes', '').strip()

        if sched_date:
            follow_up = FollowUp.objects.create(
                patient=patient,
                physician=physician,
                scheduled_date=sched_date,
                scheduled_time=sched_time if sched_time else None,
                notes=notes,
                status='SCHEDULED'
            )

            AuditLog.objects.create(
                user=request.user,
                action='APPOINTMENT_SCHEDULED',
                entity_name='FollowUp',
                entity_id=str(follow_up.id),
                details=f"Follow-up scheduled on {sched_date} for {patient.user.get_full_name()}."
            )

            messages.success(request, f"Follow-up scheduled for {patient.user.get_full_name()} on {sched_date}.")
            return redirect('physicians:patient_detail', patient_id=patient.id)

    return redirect('physicians:patient_detail', patient_id=patient.id)

