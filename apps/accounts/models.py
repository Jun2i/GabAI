from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = 'PATIENT', 'Patient'
        PHYSICIAN = 'PHYSICIAN', 'Physician / Psychiatrist'
        ADMIN = 'ADMIN', 'Administrator'
        STAFF = 'STAFF', 'Authorized Healthcare Staff'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PATIENT,
        help_text="Role determining access permissions in GabAI"
    )
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=25, blank=True, null=True)
    is_verified = models.BooleanField(
        default=False,
        help_text="Verification status for physicians and medical staff"
    )
    consent_given = models.BooleanField(
        default=False,
        help_text="Explicit consent under Philippine Data Privacy Act of 2012 (RA 10173)"
    )
    consent_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        full_name = self.get_full_name()
        return f"{full_name or self.username} ({self.get_role_display()})"

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT

    @property
    def is_physician(self):
        return self.role == self.Role.PHYSICIAN

    @property
    def is_admin_user(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_healthcare_staff(self):
        return self.role == self.Role.STAFF


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('LOGIN', 'User Login'),
        ('LOGOUT', 'User Logout'),
        ('ASSESSMENT_SUBMITTED', 'Assessment Submitted'),
        ('SAFETY_ALERT_TRIGGERED', 'Safety Alert Triggered'),
        ('AI_RECOMMENDATION_GENERATED', 'AI Recommendation Generated'),
        ('RECOMMENDATION_APPROVED', 'Recommendation Approved'),
        ('RECOMMENDATION_MODIFIED', 'Recommendation Modified & Approved'),
        ('RECOMMENDATION_REJECTED', 'Recommendation Rejected'),
        ('RECOMMENDATION_HOLD', 'Further Assessment Requested'),
        ('CLINICAL_NOTE_ADDED', 'Clinical Note Added'),
        ('APPOINTMENT_SCHEDULED', 'Appointment Scheduled'),
        ('WELLNESS_ACTIVITY_COMPLETED', 'Wellness Activity Completed'),
        ('USER_REGISTERED', 'User Registered'),
        ('CREDENTIAL_VERIFIED', 'Physician Credential Verified'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    entity_name = models.CharField(max_length=100, blank=True, null=True)
    entity_id = models.CharField(max_length=100, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    details = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.user} - {self.action}"

