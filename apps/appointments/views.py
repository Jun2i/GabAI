from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Appointment
from apps.physicians.models import PhysicianProfile
from apps.patients.models import PatientProfile
from apps.notifications.models import Notification
from apps.accounts.models import AuditLog
from apps.accounts.decorators import staff_or_physician_required
from datetime import date, time, timedelta

@login_required
def appointment_list_view(request):
    """
    List appointments for the current user (10 items per page).
    """
    if request.user.is_patient:
        patient = request.user.patient_profile
        appointments_qs = Appointment.objects.filter(patient=patient).select_related('physician__user').order_by('-appointment_date')
    elif request.user.is_physician:
        physician = request.user.physician_profile
        appointments_qs = Appointment.objects.filter(physician=physician).select_related('patient__user').order_by('-appointment_date')
    else: # Staff or Admin
        appointments_qs = Appointment.objects.select_related('patient__user', 'physician__user').order_by('-appointment_date')

    page_number = request.GET.get('page', 1)
    paginator = Paginator(appointments_qs, 10)
    try:
        appointments_page = paginator.page(page_number)
    except PageNotAnInteger:
        appointments_page = paginator.page(1)
    except EmptyPage:
        appointments_page = paginator.page(paginator.num_pages)

    context = {
        'appointments': appointments_page,
        'paginator': paginator,
        'page_obj': appointments_page,
        'today': date.today(),
    }
    return render(request, 'appointments/list.html', context)


@login_required
def request_appointment_view(request):
    """
    Patient requests a consultation or follow-up with a physician.
    Healthcare staff can also book on behalf of patients.
    """
    physicians = PhysicianProfile.objects.filter(is_verified=True).select_related('user')
    patients = PatientProfile.objects.select_related('user').all() if not request.user.is_patient else None

    if request.method == 'POST':
        physician_id = request.POST.get('physician_id')
        apt_type = request.POST.get('appointment_type', 'INITIAL_EVALUATION')
        mode = request.POST.get('consultation_mode', 'IN_PERSON')
        apt_date = request.POST.get('appointment_date')
        start_time_str = request.POST.get('start_time', '09:00')
        reason = request.POST.get('reason_for_visit', '').strip()

        if request.user.is_patient:
            patient = request.user.patient_profile
        else:
            patient_id = request.POST.get('patient_id')
            patient = get_object_or_404(PatientProfile, id=patient_id)

        physician = get_object_or_404(PhysicianProfile, id=physician_id)

        try:
            st = time.fromisoformat(start_time_str)
        except ValueError:
            st = time(9, 0)
        
        # End time default 45 mins later
        dummy_dt = timezone.datetime.combine(date.today(), st) + timedelta(minutes=45)
        et = dummy_dt.time()

        appointment = Appointment.objects.create(
            patient=patient,
            physician=physician,
            appointment_type=apt_type,
            consultation_mode=mode,
            appointment_date=apt_date,
            start_time=st,
            end_time=et,
            status='REQUESTED',
            reason_for_visit=reason or 'Mental health consultation request'
        )

        # Notify physician
        Notification.send(
            recipient=physician.user,
            notification_type='APPOINTMENT_REQUESTED',
            title=f"New Appointment Request from {patient.user.get_full_name()}",
            message=f"{patient.user.get_full_name()} requested an appointment on {apt_date} at {st.strftime('%I:%M %p')}.",
            action_url=f"/appointments/{appointment.id}/"
        )

        AuditLog.objects.create(
            user=request.user,
            action='APPOINTMENT_SCHEDULED',
            entity_name='Appointment',
            entity_id=str(appointment.id),
            details=f"Appointment requested with Dr. {physician.user.last_name} on {apt_date}."
        )

        messages.success(request, "Your appointment request has been submitted. You will receive a confirmation shortly.")
        return redirect('appointments:list')

    context = {
        'physicians': physicians,
        'patients': patients,
        'min_date': date.today().isoformat(),
    }
    return render(request, 'appointments/request.html', context)


@login_required
def appointment_detail_view(request, apt_id):
    """
    Appointment detail and status management (confirm, reschedule, complete, cancel).
    """
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient__user', 'physician__user'),
        id=apt_id
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        physician_notes = request.POST.get('physician_notes', '').strip()
        meeting_link = request.POST.get('meeting_link', '').strip()

        if action == 'CONFIRM':
            appointment.status = 'CONFIRMED'
            if meeting_link:
                appointment.meeting_link = meeting_link
            appointment.save()

            Notification.send(
                recipient=appointment.patient.user,
                notification_type='APPOINTMENT_CONFIRMED',
                title="Appointment Confirmed",
                message=f"Your appointment with Dr. {appointment.physician.user.last_name} on {appointment.appointment_date} is confirmed.",
                action_url=f"/appointments/{appointment.id}/"
            )
            messages.success(request, "Appointment confirmed.")

        elif action == 'COMPLETE':
            appointment.status = 'COMPLETED'
            appointment.save()
            messages.success(request, "Appointment marked as completed.")

        elif action == 'CANCEL':
            if request.user.is_patient and appointment.patient.user != request.user:
                messages.error(request, "Unauthorized to cancel this appointment.")
                return redirect('appointments:list')
            appointment.status = 'CANCELLED'
            appointment.save()
            messages.warning(request, "Appointment cancelled.")

        if physician_notes and (request.user.is_physician or request.user.is_healthcare_staff):
            appointment.physician_notes = physician_notes
            appointment.save()

        return redirect('appointments:detail', apt_id=appointment.id)

    context = {
        'appointment': appointment,
        'can_manage': request.user.is_physician or request.user.is_healthcare_staff or request.user.is_admin_user,
        'is_patient': request.user.is_patient,
    }
    return render(request, 'appointments/detail.html', context)

