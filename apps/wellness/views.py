from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from .models import WellnessSchedule, WellnessActivity, ActivityProgress
from apps.patients.models import PatientProfile
from apps.accounts.decorators import patient_required, staff_or_physician_required
from apps.accounts.models import AuditLog
from datetime import date, timedelta

@login_required
def schedule_view(request):
    """
    Mental Wellness Schedule View.
    Patients view their daily timeline and weekly milestones.
    Physicians/Staff can inspect schedules for specific patients.
    """
    patient = None
    if request.user.is_patient:
        patient = request.user.patient_profile
    else:
        patient_id = request.GET.get('patient_id')
        if patient_id:
            patient = get_object_or_404(PatientProfile, id=patient_id)
        else:
            patient = PatientProfile.objects.first()

    if not patient:
        messages.info(request, "No patient profile associated.")
        return redirect('accounts:dashboard_redirect')

    selected_date_str = request.GET.get('date')
    if selected_date_str:
        try:
            selected_date = date.fromisoformat(selected_date_str)
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    schedule = WellnessSchedule.objects.filter(patient=patient, status='ACTIVE').first()

    daily_activities = []
    weekly_activities = []
    completion_rate = 0.0

    if schedule:
        daily_activities = WellnessActivity.objects.filter(
            schedule=schedule,
            is_weekly=False
        ).order_by('start_time', 'order')

        weekly_activities = WellnessActivity.objects.filter(
            schedule=schedule,
            is_weekly=True
        ).order_by('order')

        total = daily_activities.count()
        completed = daily_activities.filter(status='COMPLETED').count()
        completion_rate = (completed / total * 100.0) if total > 0 else 0.0

    # Calculate streak days
    streak_count = 0
    today = date.today()
    for i in range(14):
        check_day = today - timedelta(days=i)
        day_acts = WellnessActivity.objects.filter(patient=patient, scheduled_date=check_day)
        if day_acts.exists() and day_acts.filter(status='COMPLETED').exists():
            streak_count += 1
        elif i > 0:
            break

    context = {
        'patient': patient,
        'schedule': schedule,
        'daily_activities': daily_activities,
        'weekly_activities': weekly_activities,
        'selected_date': selected_date,
        'completion_rate': round(completion_rate, 1),
        'streak_count': streak_count,
        'is_patient': request.user.is_patient,
        'total_count': total if schedule else 0,
        'completed_count': completed if schedule else 0,
    }
    return render(request, 'wellness/schedule.html', context)


@login_required
@patient_required
def update_activity_status_view(request, activity_id):
    """
    Patient updates activity status: COMPLETED, SKIPPED, or RESCHEDULED.
    """
    activity = get_object_or_404(
        WellnessActivity,
        id=activity_id,
        patient=request.user.patient_profile
    )

    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '').strip()

        if new_status in ['COMPLETED', 'SKIPPED', 'RESCHEDULED', 'PENDING']:
            activity.status = new_status
            if new_status == 'COMPLETED':
                activity.completed_at = timezone.now()
            else:
                activity.completed_at = None

            if notes:
                activity.patient_notes = notes

            activity.save()

            AuditLog.objects.create(
                user=request.user,
                action='WELLNESS_ACTIVITY_COMPLETED',
                entity_name='WellnessActivity',
                entity_id=str(activity.id),
                details=f"Activity '{activity.title}' updated to {new_status}."
            )

            messages.success(request, f"Activity '{activity.title}' marked as {activity.get_status_display()}.")

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('wellness:schedule')


@login_required
@staff_or_physician_required
def weekly_progress_summary_view(request, patient_id):
    """
    Physician / Clinical Review of patient wellness engagement and habit formation.
    """
    patient = get_object_or_404(PatientProfile, id=patient_id)
    progress_records = ActivityProgress.objects.filter(patient=patient).order_by('-week_start_date')
    recent_activities = WellnessActivity.objects.filter(patient=patient).order_by('-scheduled_date')[:30]

    context = {
        'patient': patient,
        'progress_records': progress_records,
        'recent_activities': recent_activities,
    }
    return render(request, 'wellness/weekly_summary.html', context)

