from django.db import models
from django.utils import timezone

class AiRecommendation(models.Model):
    STATUS_CHOICES = [
        ('PENDING_APPROVAL', 'Pending Physician Approval'),
        ('APPROVED', 'Approved by Physician'),
        ('MODIFIED_AND_APPROVED', 'Modified & Approved by Physician'),
        ('REJECTED', 'Rejected by Physician'),
        ('FURTHER_ASSESSMENT_REQUIRED', 'Additional Assessment Required'),
        ('COMPLETED', 'Completed Care Plan'),
    ]

    PATHWAY_CHOICES = [
        ('PATHWAY_A', 'Pathway A: Preventive Wellness Program'),
        ('PATHWAY_B', 'Pathway B: Symptom-Specific Supportive Guidance'),
    ]

    assessment = models.ForeignKey(
        'assessments.Assessment',
        on_delete=models.CASCADE,
        related_name='ai_recommendations'
    )
    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='ai_recommendations'
    )
    pathway = models.CharField(max_length=30, choices=PATHWAY_CHOICES, default='PATHWAY_A')
    status = models.CharField(
        max_length=35,
        choices=STATUS_CHOICES,
        default='PENDING_APPROVAL',
        db_index=True
    )
    title = models.CharField(max_length=255)
    summary_content = models.TextField(help_text="Overview of personalized wellness guidance")
    daily_schedule_plan = models.JSONField(
        default=list,
        help_text="Structured daily activities (exercise, meals, work/breaks, hobbies, sleep)"
    )
    weekly_activities_plan = models.JSONField(
        default=list,
        help_text="Structured weekly activities (outdoor recreation, creative, social, reflection)"
    )
    preventive_strategies = models.JSONField(
        default=list,
        help_text="Sleep hygiene, mindfulness, screen time, social connection tips"
    )
    coping_strategies = models.JSONField(
        default=list,
        help_text="Condition-tailored supportive strategies (e.g. breathing for anxiety, task breakdown for ADHD)"
    )
    lifestyle_modifications = models.TextField(blank=True, null=True)
    follow_up_guidance = models.TextField(blank=True, null=True)
    contraindication_disclaimer = models.TextField(
        default="AI recommendations are supportive wellness suggestions and do NOT replace professional clinical care, medical diagnosis, or prescription medication."
    )
    current_version = models.PositiveIntegerField(default=1)
    approved_by = models.ForeignKey(
        'physicians.PhysicianProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_recommendations'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    is_visible_to_patient = models.BooleanField(
        default=False,
        help_text="STRICT: Only True when status is APPROVED or MODIFIED_AND_APPROVED"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_recommendations'
        ordering = ['-created_at']
        verbose_name = 'AI Recommendation'
        verbose_name_plural = 'AI Recommendations'

    def __str__(self):
        return f"Recommendation #{self.id} for {self.patient.user.get_full_name()} [{self.get_status_display()}]"

    def release_to_patient(self):
        """Releases the recommendation to the patient dashboard only upon physician approval."""
        if self.status in ['APPROVED', 'MODIFIED_AND_APPROVED']:
            self.is_visible_to_patient = True
            self.save(update_fields=['is_visible_to_patient', 'updated_at'])


class RecommendationVersion(models.Model):
    MOD_TYPES = [
        ('AI_INITIAL', 'Original AI Generated Recommendation'),
        ('PHYSICIAN_MODIFICATION', 'Physician Revised & Edited'),
        ('PHYSICIAN_OVERRIDE', 'Physician Complete Custom Revision'),
    ]

    recommendation = models.ForeignKey(
        AiRecommendation,
        on_delete=models.CASCADE,
        related_name='versions'
    )
    version_number = models.PositiveIntegerField()
    modification_type = models.CharField(max_length=30, choices=MOD_TYPES, default='AI_INITIAL')
    title = models.CharField(max_length=255)
    summary_content = models.TextField()
    daily_schedule_plan = models.JSONField(default=list)
    weekly_activities_plan = models.JSONField(default=list)
    coping_strategies = models.JSONField(default=list)
    preventive_strategies = models.JSONField(default=list)
    modified_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    change_summary = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'recommendation_versions'
        unique_together = ('recommendation', 'version_number')
        ordering = ['-version_number']
        verbose_name = 'Recommendation Version'
        verbose_name_plural = 'Recommendation Versions'

    def __str__(self):
        return f"Rec #{self.recommendation_id} v{self.version_number} ({self.modification_type})"


class PhysicianApproval(models.Model):
    DECISION_CHOICES = [
        ('APPROVED', 'Approved Without Modifications'),
        ('MODIFIED_AND_APPROVED', 'Modified & Approved'),
        ('REJECTED', 'Rejected (Unsuitable / Inappropriate)'),
        ('FURTHER_ASSESSMENT_REQUESTED', 'Further Clinical Assessment Requested'),
    ]

    recommendation = models.ForeignKey(
        AiRecommendation,
        on_delete=models.CASCADE,
        related_name='approval_reviews'
    )
    physician = models.ForeignKey(
        'physicians.PhysicianProfile',
        on_delete=models.CASCADE,
        related_name='approval_reviews'
    )
    decision = models.CharField(max_length=35, choices=DECISION_CHOICES)
    reason_or_notes = models.TextField(
        help_text="Clinical justification for approval, modification, rejection, or hold"
    )
    instructions_for_patient = models.TextField(
        blank=True,
        null=True,
        help_text="Direct notes from physician accompanying the approved recommendation"
    )
    confidential_clinical_reasoning = models.TextField(
        blank=True,
        null=True,
        help_text="Internal clinical justification"
    )
    reviewed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'physician_approvals'
        ordering = ['-reviewed_at']
        verbose_name = 'Physician Approval'
        verbose_name_plural = 'Physician Approvals'

    def __str__(self):
        return f"Dr. {self.physician.user.last_name} -> Rec #{self.recommendation_id}: {self.decision}"

