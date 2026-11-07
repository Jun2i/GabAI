from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import date

class PatientProfile(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Non-Binary', 'Non-Binary'),
        ('Prefer Not to Say', 'Prefer Not to Say'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_profile'
    )
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=30, choices=GENDER_CHOICES, default='Prefer Not to Say')
    occupation = models.CharField(max_length=150, blank=True, null=True, default='Student / Working Professional')
    work_or_school_schedule = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        default='9:00 AM - 5:00 PM weekdays',
        help_text="Typical routine used by AI to generate realistic wellness schedules"
    )
    personal_interests = models.TextField(
        blank=True,
        null=True,
        default='Reading, walking, listening to music, gardening',
        help_text="Hobbies and leisure preferences for personalized wellness planning"
    )
    available_free_time = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        default='1-2 hours in evenings and weekends'
    )
    patient_preferences = models.TextField(
        blank=True,
        null=True,
        help_text="Sensory preferences, routine preferences, communication comfort levels"
    )
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, null=True)
    assigned_physician = models.ForeignKey(
        'physicians.PhysicianProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_patients'
    )
    has_active_safety_alert = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Urgent flag indicating positive suicidal ideation or acute safety concern"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'patient_profiles'
        verbose_name = 'Patient Profile'
        verbose_name_plural = 'Patient Profiles'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} (DOB: {self.date_of_birth})"

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

