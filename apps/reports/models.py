from django.db import models
from django.conf import settings
from django.utils import timezone

class GeneratedReport(models.Model):
    REPORT_TYPES = [
        ('PATIENT_SCREENING', 'Individual Patient Screening Report'),
        ('AI_RECOMMENDATION_AUDIT', 'AI Recommendation & Physician Audit Report'),
        ('WELLNESS_PROGRESS', 'Wellness Activity Progress Report'),
        ('ASSESSMENT_TRENDS', 'Patient Assessment History & Trend Report'),
        ('CLINICAL_SUMMARY', 'Physician Clinical Evaluation Summary'),
    ]

    report_type = models.CharField(max_length=40, choices=REPORT_TYPES)
    title = models.CharField(max_length=255)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='generated_reports'
    )
    assessment = models.ForeignKey(
        'assessments.Assessment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    data_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']
        verbose_name = 'Generated Report'
        verbose_name_plural = 'Generated Reports'

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.title} ({self.created_at.strftime('%Y-%m-%d')})"

