from django.db import models
from django.conf import settings
from django.utils import timezone

class PhysicianProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='physician_profile'
    )
    license_number = models.CharField(max_length=50, unique=True)
    specialization = models.CharField(max_length=150, default='General Psychiatry')
    hospital_affiliation = models.CharField(max_length=200, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    consultation_hours = models.CharField(max_length=100, default='Mon-Fri 9:00 AM - 5:00 PM')
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_physicians'
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'physician_profiles'
        verbose_name = 'Physician Profile'
        verbose_name_plural = 'Physician Profiles'

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username} ({self.specialization})"


class HealthcareStaff(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_profile'
    )
    department = models.CharField(max_length=100, default='Triage & Patient Intake')
    staff_id = models.CharField(max_length=50, unique=True)
    can_register_patients = models.BooleanField(default=True)
    can_forward_cases = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'healthcare_staff'
        verbose_name = 'Healthcare Staff'
        verbose_name_plural = 'Healthcare Staff'

    def __str__(self):
        return f"Staff {self.user.get_full_name() or self.user.username} - {self.department}"


class ClinicalRecord(models.Model):
    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='clinical_records'
    )
    physician = models.ForeignKey(
        PhysicianProfile,
        on_delete=models.CASCADE,
        related_name='clinical_records'
    )
    assessment = models.ForeignKey(
        'assessments.Assessment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clinical_records'
    )
    clinical_findings = models.TextField(
        help_text="Physician-confirmed clinical observations and evaluation findings"
    )
    clinical_diagnosis = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Official medical diagnosis made solely by physician"
    )
    treatment_plan = models.TextField(
        blank=True,
        null=True,
        help_text="Physician-authorized treatment plan"
    )
    follow_up_instructions = models.TextField(blank=True, null=True)
    confidential_notes = models.TextField(
        blank=True,
        null=True,
        help_text="Internal confidential notes accessible only to clinical team"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'clinical_records'
        ordering = ['-created_at']
        verbose_name = 'Clinical Record'
        verbose_name_plural = 'Clinical Records'

    def __str__(self):
        return f"Clinical Note for {self.patient.user.get_full_name()} by Dr. {self.physician.user.last_name}"


class FollowUp(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('OVERDUE', 'Overdue'),
    ]

    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='follow_ups'
    )
    physician = models.ForeignKey(
        PhysicianProfile,
        on_delete=models.CASCADE,
        related_name='assigned_follow_ups'
    )
    clinical_record = models.ForeignKey(
        ClinicalRecord,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='follow_up_details'
    )
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'follow_ups'
        ordering = ['scheduled_date', 'scheduled_time']
        verbose_name = 'Follow-up'
        verbose_name_plural = 'Follow-ups'

    def __str__(self):
        return f"Follow-up: {self.patient.user.get_full_name()} with Dr. {self.physician.user.last_name} on {self.scheduled_date}"

