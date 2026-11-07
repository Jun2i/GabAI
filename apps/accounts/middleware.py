from django.shortcuts import redirect
from django.urls import reverse

class ConsentVerificationMiddleware:
    """
    Ensures Patients have explicitly reviewed and accepted the
    Philippine Data Privacy Act (RA 10173) and Clinical Consent
    before accessing assessments or health records.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.is_patient:
            consent_url = reverse('accounts:privacy_consent')
            logout_url = reverse('accounts:logout')
            login_url = reverse('accounts:login')
            static_prefix = '/static/'
            media_prefix = '/media/'
            
            allowed_paths = [consent_url, logout_url, login_url]
            current_path = request.path

            if not request.user.consent_given:
                if not any(current_path.startswith(p) for p in allowed_paths) and \
                   not current_path.startswith(static_prefix) and \
                   not current_path.startswith(media_prefix):
                    return redirect('accounts:privacy_consent')

        response = self.get_response(request)
        return response

