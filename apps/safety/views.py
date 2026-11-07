from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import SafetyAssessment
from apps.accounts.decorators import staff_or_physician_required
from apps.accounts.models import AuditLog
from apps.physicians.models import PhysicianProfile

@login_required
def crisis_resources_view(request):
    """
    Patient-facing 24/7 crisis hotlines & immediate emergency resources.
    Highlighted prominently in the Philippines context (NCMH 1553, Hopeline)
    and emergency services.
    """
    patient = getattr(request.user, 'patient_profile', None)
    latest_safety_alert = None
    if patient:
        latest_safety_alert = SafetyAssessment.objects.filter(
            patient=patient,
            status__in=['ACTIVE_EMERGENCY', 'UNDER_CLINICAL_REVIEW']
        ).first()

    context = {
        'patient': patient,
        'latest_safety_alert': latest_safety_alert,
    }
    return render(request, 'safety/crisis_resources.html', context)


@login_required
@staff_or_physician_required
def emergency_management_view(request):
    """
    Clinical Emergency Monitoring Dashboard for physicians and clinical staff.
    Lists all active safety cases requiring urgent human intervention.
    """
    active_cases = SafetyAssessment.objects.filter(
        status__in=['ACTIVE_EMERGENCY', 'UNDER_CLINICAL_REVIEW']
    ).select_related('patient__user', 'escalated_to__user').order_by('-created_at')

    resolved_cases = SafetyAssessment.objects.filter(
        status__in=['INTERVENTION_INITIATED', 'RESOLVED']
    ).select_related('patient__user', 'resolved_by__user').order_by('-resolved_at')[:10]

    context = {
        'active_cases': active_cases,
        'resolved_cases': resolved_cases,
    }
    return render(request, 'safety/emergency_management.html', context)


@login_required
@staff_or_physician_required
def emergency_detail_view(request, safety_id):
    """
    Individual safety case detail and clinical intervention documentation.
    Allows physician to record actions taken, contact emergency contact, and resolve alert.
    """
    safety = get_object_or_404(
        SafetyAssessment.objects.select_related('patient__user', 'assessment'),
        id=safety_id
    )

    if request.method == 'POST':
        action = request.POST.get('action')
        notes = request.POST.get('action_taken', '').strip()
        physician_profile = PhysicianProfile.objects.filter(user=request.user).first()

        if action == 'INITIATE_INTERVENTION':
            safety.status = 'INTERVENTION_INITIATED'
            safety.action_taken = (safety.action_taken or '') + f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M')}] {request.user.get_full_name()}: {notes}"
            safety.save()
            messages.info(request, "Intervention status initiated and documented.")
            return redirect('safety:detail', safety_id=safety.id)

        elif action == 'RESOLVE_EMERGENCY':
            safety.status = 'RESOLVED'
            safety.action_taken = (safety.action_taken or '') + f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M')} RESOLVED] {request.user.get_full_name()}: {notes}"
            safety.resolved_by = physician_profile
            safety.resolved_at = timezone.now()
            safety.save()

            # Clear patient active safety alert flag if no other active emergencies exist
            patient = safety.patient
            other_active = SafetyAssessment.objects.filter(
                patient=patient,
                status__in=['ACTIVE_EMERGENCY', 'UNDER_CLINICAL_REVIEW']
            ).exclude(id=safety.id).exists()
            if not other_active:
                patient.has_active_safety_alert = False
                patient.save(update_fields=['has_active_safety_alert'])

            AuditLog.objects.create(
                user=request.user,
                action='SAFETY_ALERT_TRIGGERED',
                entity_name='SafetyAssessment',
                entity_id=str(safety.id),
                details=f"Safety emergency resolved by {request.user.get_full_name()}. Resolution notes: {notes}"
            )

            messages.success(request, f"Safety case #{safety.id} resolved and documented.")
            return redirect('safety:management')

    context = {
        'safety': safety,
        'patient': safety.patient,
        'emergency_contact': {
            'name': safety.patient.emergency_contact_name,
            'phone': safety.patient.emergency_contact_phone,
            'relationship': safety.patient.emergency_contact_relationship
        }
    }
    return render(request, 'safety/emergency_detail.html', context)

