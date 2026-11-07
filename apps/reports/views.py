from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from apps.assessments.models import Assessment, ScreeningResult
from apps.recommendations.models import AiRecommendation, PhysicianApproval
from apps.patients.models import PatientProfile
from apps.wellness.models import WellnessActivity, ActivityProgress
from apps.accounts.models import AuditLog
from apps.accounts.decorators import staff_or_physician_required, admin_required
from datetime import date, timedelta

@login_required
def screening_report_view(request, assessment_id):
    """
    Formal Clinical Screening Report.
    Includes patient info, scoring breakdown, standard instrument totals (PHQ-9, GAD-7),
    AI summary, physician notes, and statutory clinical disclaimers.
    Printable & ready for PDF export.
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
        'patient': assessment.patient,
        'results': results,
        'recommendation': recommendation,
        'ai_analysis': ai_analysis,
        'report_date': date.today(),
    }
    return render(request, 'reports/screening_report.html', context)


@login_required
def recommendation_report_view(request, rec_id):
    """
    Physician-Approved Recommendation Audit Report.
    Displays physician sign-off, full text, version history, and schedule breakdown.
    """
    recommendation = get_object_or_404(
        AiRecommendation.objects.select_related('patient__user', 'approved_by__user', 'assessment'),
        id=rec_id
    )

    if request.user.is_patient and recommendation.patient.user != request.user:
        messages.error(request, "Access unauthorized.")
        return redirect('patients:dashboard')

    approvals = recommendation.approval_reviews.select_related('physician__user').all()

    context = {
        'recommendation': recommendation,
        'patient': recommendation.patient,
        'approvals': approvals,
        'report_date': date.today(),
    }
    return render(request, 'reports/recommendation_report.html', context)


@login_required
@staff_or_physician_required
def clinical_analytics_view(request):
    """
    Aggregated screening statistics, category elevation breakdown,
    and wellness activity completion analytics.
    """
    total_assessments = Assessment.objects.count()
    total_recs = AiRecommendation.objects.count()
    approved_recs = AiRecommendation.objects.filter(status__in=['APPROVED', 'MODIFIED_AND_APPROVED']).count()
    rejected_recs = AiRecommendation.objects.filter(status='REJECTED').count()
    hold_recs = AiRecommendation.objects.filter(status='FURTHER_ASSESSMENT_REQUIRED').count()
    pending_recs = AiRecommendation.objects.filter(status='PENDING_APPROVAL').count()

    total_activities = WellnessActivity.objects.count()
    completed_activities = WellnessActivity.objects.filter(status='COMPLETED').count()

    # Elevated category counts
    from apps.assessments.models import QuestionnaireCategory
    categories = QuestionnaireCategory.objects.all().order_by('category_order')
    category_stats = []
    for cat in categories:
        elevated_count = ScreeningResult.objects.filter(category=cat, is_elevated=True).count()
        total_cat_res = ScreeningResult.objects.filter(category=cat).count()
        pct = (elevated_count / total_cat_res * 100.0) if total_cat_res > 0 else 0.0
        category_stats.append({
            'name': cat.name,
            'elevated_count': elevated_count,
            'percentage': round(pct, 1)
        })

    context = {
        'total_assessments': total_assessments,
        'total_recs': total_recs,
        'approved_recs': approved_recs,
        'rejected_recs': rejected_recs,
        'hold_recs': hold_recs,
        'pending_recs': pending_recs,
        'total_activities': total_activities,
        'completed_activities': completed_activities,
        'category_stats': category_stats,
    }
    return render(request, 'reports/analytics.html', context)


@login_required
@staff_or_physician_required
def audit_log_view(request):
    """
    System Audit Log Browser with 10 items per page pagination.
    """
    action_filter = request.GET.get('action')
    logs_qs = AuditLog.objects.select_related('user').order_by('-timestamp')

    if action_filter:
        logs_qs = logs_qs.filter(action=action_filter)

    page_number = request.GET.get('page', 1)
    paginator = Paginator(logs_qs, 10)
    try:
        logs_page = paginator.page(page_number)
    except PageNotAnInteger:
        logs_page = paginator.page(1)
    except EmptyPage:
        logs_page = paginator.page(paginator.num_pages)

    context = {
        'logs': logs_page,
        'paginator': paginator,
        'page_obj': logs_page,
        'action_choices': AuditLog.ACTION_CHOICES,
        'current_action': action_filter,
    }
    return render(request, 'reports/audit_logs.html', context)

