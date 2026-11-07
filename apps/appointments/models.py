from django.db import models
from django.utils import timezone
from datetime import date

class Appointment(models.Model):
    STATUS_CHOICES = [
        ('REQUESTED', 'Requested (Pending Confirmation)'),
        ('CONFIRMED', 'Confirmed & Scheduled'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('RESCHEDULED', 'Rescheduled'),
    ]

    APPOINTMENT_TYPES = [
        ('INITIAL_EVALUATION', 'Initial Psychiatric / Psychological Evaluation'),
        ('FOLLOW_UP', 'Follow-up Consultation'),
        ('CLINICAL_INTERVIEW', 'Clinical Interview for Further Assessment'),
        ('WELLNESS_CHECK', 'Preventive Wellness Check-in'),
        ('URGENT_SAFETY', 'Priority Clinical Safety Evaluation'),
    ]

    MODE_CHOICES = [
        ('IN_PERSON', 'In-Person (Clinic Consultation)'),
        ('TELEHEALTH', 'Secure Telehealth Video Call'),
    ]

    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    physician = models.ForeignKey(
        'physicians.PhysicianProfile',
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    appointment_type = models.CharField(
        max_length=30,
        choices=APPOINTMENT_TYPES,
        default='INITIAL_EVALUATION'
    )
    consultation_mode = models.CharField(
        max_length=20,
        choices=MODE_CHOICES,
        default='IN_PERSON'
    )
    appointment_date = models.DateField(default=date.today)
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='REQUESTED',
        db_index=True
    )
    reason_for_visit = models.TextField(help_text="Patient reported reason or symptom summary")
    physician_notes = models.TextField(blank=True, null=True)
    meeting_link = models.URLField(blank=True, null=True, help_text="Telehealth video meeting link")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'appointments'
        ordering = ['appointment_date', 'start_time']
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'

    def __str__(self):
        return f"{self.get_appointment_type_display()}: {self.patient.user.get_full_name()} with Dr. {self.physician.user.last_name} on {self.appointment_date}"

