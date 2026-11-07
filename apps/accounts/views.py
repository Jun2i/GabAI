from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import User, AuditLog
from .forms import LoginForm, PatientRegistrationForm, PhysicianRegistrationForm
from apps.patients.models import PatientProfile
from apps.physicians.models import PhysicianProfile
from apps.accounts.decorators import admin_required

def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            user = form.user
            login(request, user)
            AuditLog.objects.create(
                user=user,
                action='LOGIN',
                details=f"User {user.username} logged in successfully."
            )
            messages.success(request, f"Welcome back, {user.first_name or user.username}!")
            return redirect('accounts:dashboard_redirect')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    AuditLog.objects.create(
        user=request.user,
        action='LOGOUT',
        details=f"User {request.user.username} logged out."
    )
    logout(request)
    messages.info(request, "You have been securely logged out.")
    return redirect('accounts:login')


def register_patient_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.PATIENT
            user.set_password(form.cleaned_data['password'])
            user.is_verified = True
            user.consent_given = False # Will require consent on next step
            user.save()

            # Create patient profile
            PatientProfile.objects.create(
                user=user,
                date_of_birth=form.cleaned_data.get('date_of_birth'),
                gender=form.cleaned_data.get('gender', 'Prefer Not to Say'),
                emergency_contact_name=form.cleaned_data.get('emergency_contact_name'),
                emergency_contact_phone=form.cleaned_data.get('emergency_contact_phone'),
                emergency_contact_relationship=form.cleaned_data.get('emergency_contact_relationship'),
            )

            AuditLog.objects.create(
                user=user,
                action='USER_REGISTERED',
                details=f"Patient account registered for {user.username}."
            )

            login(request, user)
            messages.success(request, "Registration successful! Please review and acknowledge the Data Privacy Consent.")
            return redirect('accounts:privacy_consent')
    else:
        form = PatientRegistrationForm()

    return render(request, 'accounts/register_patient.html', {'form': form})


def register_physician_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')

    if request.method == 'POST':
        form = PhysicianRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = User.Role.PHYSICIAN
            user.set_password(form.cleaned_data['password'])
            user.is_verified = False # Requires administrator credential check
            user.consent_given = True
            user.save()

            # Create physician profile
            PhysicianProfile.objects.create(
                user=user,
                license_number=form.cleaned_data.get('license_number'),
                specialization=form.cleaned_data.get('specialization'),
                hospital_affiliation=form.cleaned_data.get('hospital_affiliation'),
                is_verified=False
            )

            AuditLog.objects.create(
                user=user,
                action='USER_REGISTERED',
                details=f"Physician account registered for Dr. {user.username} (PRC: {form.cleaned_data.get('license_number')}). Awaiting admin verification."
            )

            login(request, user)
            messages.info(request, "Account created. As a licensed medical practitioner, your credentials will be verified by the administrator.")
            return redirect('accounts:dashboard_redirect')
    else:
        form = PhysicianRegistrationForm()

    return render(request, 'accounts/register_physician.html', {'form': form})


@login_required
def privacy_consent_view(request):
    """
    Patient Consent under Philippine Data Privacy Act of 2012 (RA 10173).
    Ensures that patient explicitly consents to mental health data processing
    and acknowledges the clinical boundaries of AI screening.
    """
    if request.method == 'POST':
        consent = request.POST.get('consent_agreed')
        if consent == 'on' or consent == '1':
            request.user.consent_given = True
            request.user.consent_date = timezone.now()
            request.user.save(update_fields=['consent_given', 'consent_date'])

            AuditLog.objects.create(
                user=request.user,
                action='LOGIN',
                details="Patient acknowledged RA 10173 Data Privacy & Non-Diagnostic AI Disclaimer."
            )

            messages.success(request, "Data Privacy Consent acknowledged. Welcome to GabAI!")
            return redirect('patients:dashboard')
        else:
            messages.error(request, "You must check the consent agreement to proceed.")

    return render(request, 'accounts/privacy_consent.html')


@login_required
def dashboard_redirect_view(request):
    """
    Smart router redirecting user to appropriate dashboard based on assigned role.
    """
    user = request.user
    if user.is_admin_user:
        return redirect('accounts:admin_dashboard')
    elif user.is_physician or user.is_healthcare_staff:
        return redirect('physicians:dashboard')
    else:
        return redirect('patients:dashboard')


@login_required
@admin_required
def admin_dashboard_view(request):
    """
    Administrator Dashboard.
    Manages accounts, verifies physician credentials, reviews system logs, and inspects AI templates.
    Displays 10 physicians per page with clean pagination.
    """
    total_users = User.objects.count()
    patients_count = PatientProfile.objects.count()
    physicians_qs = PhysicianProfile.objects.select_related('user').all().order_by('id')
    total_physicians_count = physicians_qs.count()
    unverified_physicians_count = physicians_qs.filter(is_verified=False).count()

    page_number = request.GET.get('page', 1)
    paginator = Paginator(physicians_qs, 10)
    try:
        physicians_page = paginator.page(page_number)
    except PageNotAnInteger:
        physicians_page = paginator.page(1)
    except EmptyPage:
        physicians_page = paginator.page(paginator.num_pages)

    audit_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]

    context = {
        'total_users': total_users,
        'patients_count': patients_count,
        'total_physicians_count': total_physicians_count,
        'unverified_count': unverified_physicians_count,
        'physicians': physicians_page,
        'paginator': paginator,
        'page_obj': physicians_page,
        'audit_logs': audit_logs,
    }
    return render(request, 'accounts/admin_dashboard.html', context)


@login_required
@admin_required
def verify_physician_view(request, physician_id):
    """
    Admin verifies or revokes verification of a physician.
    """
    physician = get_object_or_404(PhysicianProfile, id=physician_id)
    physician.is_verified = not physician.is_verified
    if physician.is_verified:
        physician.verified_at = timezone.now()
        physician.verified_by = request.user
        physician.user.is_verified = True
    else:
        physician.verified_at = None
        physician.verified_by = None
        physician.user.is_verified = False
    
    physician.save()
    physician.user.save()

    AuditLog.objects.create(
        user=request.user,
        action='CREDENTIAL_VERIFIED',
        entity_name='PhysicianProfile',
        entity_id=str(physician.id),
        details=f"Admin updated verification for Dr. {physician.user.last_name}: {'Verified' if physician.is_verified else 'Unverified'}."
    )

    messages.success(request, f"Physician Dr. {physician.user.get_full_name()} status updated to: {'Verified' if physician.is_verified else 'Unverified'}.")
    return redirect('accounts:admin_dashboard')

