from django.db import models
from django.utils import timezone

class SafetyAssessment(models.Model):
    URGENCY_CHOICES = [
        ('CRITICAL', 'Critical Immediate Danger (Current Plan/Intent)'),
        ('HIGH', 'High Risk (Suicidal Ideation / Inability to Guarantee Safety)'),
        ('MODERATE', 'Elevated Concern (Past Self-Harm / Passive Ideation)'),
        ('NONE', 'No Current Crisis Reported'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE_EMERGENCY', 'Active Emergency - Immediate Action Required'),
        ('UNDER_CLINICAL_REVIEW', 'Under Clinical Review'),
        ('INTERVENTION_INITIATED', 'Human Clinical Intervention Initiated'),
        ('RESOLVED', 'Safety Protocol Resolved & Documented'),
    ]

    assessment = models.ForeignKey(
        'assessments.Assessment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='safety_assessments'
    )
    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='safety_assessments'
    )
    intent_reported = models.BooleanField(default=False)
    plan_reported = models.BooleanField(default=False)
    inability_to_stay_safe = models.BooleanField(default=False)
    immediate_danger = models.BooleanField(default=False)
    urgency_level = models.CharField(max_length=30, choices=URGENCY_CHOICES, default='CRITICAL')
    status = models.CharField(max_length=35, choices=STATUS_CHOICES, default='ACTIVE_EMERGENCY')
    safety_triggers_detected = models.TextField(
        help_text="Detailed trigger questions and patient responses that activated safety alert"
    )
    escalated_to = models.ForeignKey(
        'physicians.PhysicianProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='escalated_safety_cases'
    )
    escalated_at = models.DateTimeField(default=timezone.now)
    action_taken = models.TextField(blank=True, null=True)
    emergency_contacted = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        'physicians.PhysicianProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_safety_cases'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'safety_assessments'
        ordering = ['-created_at']
        verbose_name = 'Safety Assessment'
        verbose_name_plural = 'Safety Assessments'

    def __str__(self):
        return f"SAFETY ALERT [{self.urgency_level}] - {self.patient.user.get_full_name()} ({self.status})"

