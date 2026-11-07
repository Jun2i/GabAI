from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import PatientProfile
from apps.assessments.models import Assessment
from apps.recommendations.models import AiRecommendation
from apps.wellness.models import WellnessSchedule, WellnessActivity
from apps.appointments.models import Appointment
from apps.physicians.models import FollowUp
from apps.notifications.models import Notification
from apps.accounts.decorators import patient_required
from datetime import date, timedelta

@login_required
@patient_required
def patient_dashboard_view(request):
    """
    Patient Recommendation & Mental Wellness Dashboard.
    Displays only physician-approved recommendations, active schedule,
    completion metrics, upcoming appointments, and follow-ups.
    """
    patient = request.user.patient_profile

    # Latest assessment and status
    latest_assessment = Assessment.objects.filter(patient=patient).order_by('-created_at').first()

    # Recommendations:
    # All recommendations for this patient (with distinct status badges and preloaded relations)
    recommendations_qs = AiRecommendation.objects.filter(
        patient=patient
    ).select_related('approved_by__user', 'assessment').order_by('-created_at')

    # Latest physician-approved recommendation for active care display
    approved_recommendation = recommendations_qs.filter(
        status__in=['APPROVED', 'MODIFIED_AND_APPROVED'],
        is_visible_to_patient=True
    ).first()

    page_number = request.GET.get('page', 1)
    paginator = Paginator(recommendations_qs, 10)
    try:
        recommendations_page = paginator.page(page_number)
    except PageNotAnInteger:
        recommendations_page = paginator.page(1)
    except EmptyPage:
        recommendations_page = paginator.page(paginator.num_pages)

    # Active wellness schedule & today's activities
    active_schedule = WellnessSchedule.objects.filter(patient=patient, status='ACTIVE').first()
    today_activities = []
    weekly_activities = []
    completion_rate = 0.0

    if active_schedule:
        today_activities = WellnessActivity.objects.filter(
            schedule=active_schedule,
            scheduled_date=date.today(),
            is_weekly=False
        ).order_by('start_time', 'order')

        weekly_activities = WellnessActivity.objects.filter(
            schedule=active_schedule,
            is_weekly=True
        ).order_by('order')

        total = today_activities.count()
        completed = today_activities.filter(status='COMPLETED').count()
        completion_rate = (completed / total * 100.0) if total > 0 else 0.0

    # Upcoming Appointments
    upcoming_appointments = Appointment.objects.filter(
        patient=patient,
        appointment_date__gte=date.today(),
        status__in=['REQUESTED', 'CONFIRMED']
    ).select_related('physician__user').order_by('appointment_date', 'start_time')[:3]

    # Upcoming Follow-ups
    upcoming_followups = FollowUp.objects.filter(
        patient=patient,
        scheduled_date__gte=date.today(),
        status='SCHEDULED'
    ).select_related('physician__user').order_by('scheduled_date')[:3]

    # Recent notifications
    recent_notifications = Notification.objects.filter(
        recipient=request.user
    ).order_by('-created_at')[:5]

    context = {
        'patient': patient,
        'latest_assessment': latest_assessment,
        'recommendations': recommendations_page,
        'paginator': paginator,
        'page_obj': recommendations_page,
        'total_recs_count': recommendations_qs.count(),
        'approved_recommendation': approved_recommendation,
        'active_schedule': active_schedule,
        'today_activities': today_activities,
        'weekly_activities': weekly_activities,
        'completion_rate': round(completion_rate, 1),
        'upcoming_appointments': upcoming_appointments,
        'upcoming_followups': upcoming_followups,
        'recent_notifications': recent_notifications,
        'today': date.today(),
    }
    return render(request, 'patients/dashboard.html', context)


@login_required
@patient_required
def patient_profile_view(request):
    """
    Patient Profile and Preferences Management.
    Enables patient to update routine, hobbies, and preferences used by AI Scheduler.
    """
    patient = request.user.patient_profile

    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name).strip()
        user.last_name = request.POST.get('last_name', user.last_name).strip()
        user.phone_number = request.POST.get('phone_number', user.phone_number).strip()
        user.save()

        patient.occupation = request.POST.get('occupation', patient.occupation).strip()
        patient.work_or_school_schedule = request.POST.get('work_or_school_schedule', patient.work_or_school_schedule).strip()
        patient.personal_interests = request.POST.get('personal_interests', patient.personal_interests).strip()
        patient.available_free_time = request.POST.get('available_free_time', patient.available_free_time).strip()
        patient.patient_preferences = request.POST.get('patient_preferences', patient.patient_preferences).strip()
        patient.emergency_contact_name = request.POST.get('emergency_contact_name', patient.emergency_contact_name).strip()
        patient.emergency_contact_phone = request.POST.get('emergency_contact_phone', patient.emergency_contact_phone).strip()
        patient.emergency_contact_relationship = request.POST.get('emergency_contact_relationship', patient.emergency_contact_relationship).strip()
        patient.save()

        messages.success(request, "Your personal wellness profile and preferences have been updated.")
        return redirect('patients:profile')

    context = {
        'patient': patient,
        'user': request.user,
    }
    return render(request, 'patients/profile.html', context)

