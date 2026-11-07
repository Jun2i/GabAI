from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                messages.error(request, "Access denied: You do not have permission to access this healthcare module.")
                return redirect('accounts:dashboard_redirect')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def patient_required(view_func):
    return role_required('PATIENT')(view_func)

def physician_required(view_func):
    return role_required('PHYSICIAN')(view_func)

def staff_or_physician_required(view_func):
    return role_required('PHYSICIAN', 'STAFF', 'ADMIN')(view_func)

def admin_required(view_func):
    return role_required('ADMIN')(view_func)

