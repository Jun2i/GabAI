from .models import SafetyAssessment

def safety_alert_context(request):
    """
    Context processor to make active emergency safety alerts immediately
    prominent to clinical staff and physicians.
    """
    if request.user.is_authenticated:
        if request.user.is_physician or request.user.is_healthcare_staff or request.user.is_admin_user:
            active_emergencies = SafetyAssessment.objects.filter(
                status__in=['ACTIVE_EMERGENCY', 'UNDER_CLINICAL_REVIEW']
            ).select_related('patient__user')
            return {
                'active_emergency_alerts': active_emergencies,
                'active_emergency_count': active_emergencies.count(),
            }
        elif request.user.is_patient and hasattr(request.user, 'patient_profile'):
            has_alert = request.user.patient_profile.has_active_safety_alert
            return {
                'patient_has_safety_alert': has_alert
            }
    return {
        'active_emergency_alerts': [],
        'active_emergency_count': 0,
        'patient_has_safety_alert': False,
    }

