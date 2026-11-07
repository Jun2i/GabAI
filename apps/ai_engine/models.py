from django.db import models
from django.utils import timezone

class AiAnalysis(models.Model):
    PATHWAY_CHOICES = [
        ('PATHWAY_A', 'Pathway A: Preventive Mental Wellness (No Significant Screening Concerns)'),
        ('PATHWAY_B', 'Pathway B: Supportive Guidance (Reported Mental Health Concerns)'),
    ]

    assessment = models.OneToOneField(
        'assessments.Assessment',
        on_delete=models.CASCADE,
        related_name='ai_analysis'
    )
    analysis_pathway = models.CharField(
        max_length=30,
        choices=PATHWAY_CHOICES,
        default='PATHWAY_A'
    )
    frequently_reported_symptoms = models.JSONField(
        default=list,
        help_text="Identified symptoms reported as 'Nearly every day' or 'More than half the days'"
    )
    elevated_categories = models.JSONField(
        default=list,
        help_text="Categories with moderate, elevated, or high symptom frequencies"
    )
    identified_patterns = models.TextField(
        blank=True,
        null=True,
        help_text="Possible co-occurring patterns observed across screening domains"
    )
    daily_activity_effects = models.TextField(
        blank=True,
        null=True,
        help_text="Reported interference with work, study, relationships, or daily routine"
    )
    areas_for_investigation = models.TextField(
        blank=True,
        null=True,
        help_text="Specific domains recommended for physician exploration during clinical interview"
    )
    missing_or_incomplete_notes = models.TextField(
        blank=True,
        null=True,
        default="All required screening items were completed."
    )
    safety_concerns_flagged = models.BooleanField(
        default=False,
        help_text="Explicit alert if safety items are triggered"
    )
    safety_summary = models.TextField(
        blank=True,
        null=True
    )
    physician_readable_summary = models.TextField(
        help_text="Readable clinical summary tailored for physician review. Strictly non-diagnostic."
    )
    is_diagnostic = models.BooleanField(
        default=False,
        help_text="Mandatory False: AI never diagnoses a condition"
    )
    model_used = models.CharField(max_length=100, default='GabAI Clinical LLM Engine')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ai_analysis'
        ordering = ['-created_at']
        verbose_name = 'AI Assessment Analysis'
        verbose_name_plural = 'AI Assessment Analyses'

    def __str__(self):
        return f"AI Analysis for Assessment #{self.assessment_id} ({self.get_analysis_pathway_display()})"

