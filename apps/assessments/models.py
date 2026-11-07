from django.db import models
from django.utils import timezone

class QuestionnaireCategory(models.Model):
    CATEGORY_CODES = [
        ('ANXIETY', 'Anxiety'),
        ('DEPRESSION', 'Depression'),
        ('STRESS', 'Stress'),
        ('EMOTIONAL_WELLBEING', 'Emotional Well-being'),
        ('SLEEP_DAILY', 'Sleep and Daily Activities'),
        ('SAFETY', 'Safety and Self-Harm'),
        # Legacy mappings for backward compatibility
        ('ADHD', 'ADHD-Related Symptoms'),
        ('BIPOLAR', 'Bipolar-Related Symptoms'),
        ('OCD', 'OCD-Related Symptoms'),
        ('PTSD', 'PTSD-Related Symptoms'),
        ('AUTISM', 'Autism-Related Developmental Traits'),
        ('SLEEP', 'Sleep-Related Concerns'),
        ('EATING', 'Eating-Related Concerns'),
        ('PSYCHOSIS', 'Psychosis-Related Experiences'),
        ('SUBSTANCE', 'Substance Use Concerns'),
    ]

    code = models.CharField(max_length=50, choices=CATEGORY_CODES, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField()
    category_order = models.PositiveIntegerField(default=1)
    is_developmental = models.BooleanField(
        default=False,
        help_text="Requires developmental scale (Yes/No/Unsure/Prefer not to answer) and longer-term context"
    )
    is_critical_safety = models.BooleanField(
        default=False,
        help_text="Immediate emergency workflow triggered upon positive responses"
    )
    disclaimer = models.TextField(
        default="This screening tool is an informational aid and does not constitute a formal clinical diagnosis."
    )

    class Meta:
        db_table = 'questionnaire_categories'
        ordering = ['category_order']
        verbose_name = 'Questionnaire Category'
        verbose_name_plural = 'Questionnaire Categories'

    def __str__(self):
        return f"{self.category_order}. {self.name}"


class Question(models.Model):
    QUESTION_TYPES = [
        ('FREQUENCY', 'Frequency (Not at all, Several days, More than half the days, Nearly every day)'),
        ('DEVELOPMENTAL', 'Developmental (Yes, No, Unsure, Prefer not to answer)'),
        ('YES_NO', 'Binary Yes/No'),
    ]

    category = models.ForeignKey(
        QuestionnaireCategory,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default='FREQUENCY')
    order = models.PositiveIntegerField(default=1)
    is_critical_safety = models.BooleanField(
        default=False,
        help_text="True if positive answer indicates suicidal intent, plan, or acute harm"
    )
    help_text = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        db_table = 'questions'
        ordering = ['category__category_order', 'order']
        verbose_name = 'Question'
        verbose_name_plural = 'Questions'

    def __str__(self):
        return f"[{self.category.name}] Q{self.order}: {self.question_text[:60]}..."


class Assessment(models.Model):
    STATUS_CHOICES = [
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted & Pending AI Analysis'),
        ('ANALYZED', 'AI Analyzed - Pending Physician Review'),
        ('REVIEWED', 'Physician Reviewed'),
        ('COMPLETED', 'Completed & Released'),
    ]

    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='assessments'
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='IN_PROGRESS')
    phq9_score = models.IntegerField(null=True, blank=True)
    phq9_severity = models.CharField(max_length=50, blank=True, null=True)
    gad7_score = models.IntegerField(null=True, blank=True)
    gad7_severity = models.CharField(max_length=50, blank=True, null=True)
    stress_score = models.IntegerField(null=True, blank=True)
    has_safety_flag = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Immediate safety alert triggered"
    )
    completion_rate = models.FloatField(default=0.0)
    total_questions_answered = models.IntegerField(default=0)
    disclaimer_accepted = models.BooleanField(
        default=True,
        help_text="Patient acknowledged that screening is non-diagnostic"
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assessments'
        ordering = ['-created_at']
        verbose_name = 'Assessment'
        verbose_name_plural = 'Assessments'

    def __str__(self):
        return f"Assessment #{self.id} - {self.patient.user.get_full_name()} ({self.get_status_display()})"


class PatientResponse(models.Model):
    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='responses'
    )
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='patient_responses'
    )
    response_value = models.CharField(max_length=100)
    numeric_score = models.FloatField(default=0.0)
    response_label = models.CharField(max_length=100)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'patient_responses'
        unique_together = ('assessment', 'question')
        verbose_name = 'Patient Response'
        verbose_name_plural = 'Patient Responses'

    def __str__(self):
        return f"Resp A{self.assessment_id} Q{self.question_id}: {self.response_label}"


class ScreeningResult(models.Model):
    SEVERITY_LEVELS = [
        ('MINIMAL', 'Minimal / No Concern'),
        ('MILD', 'Mild'),
        ('MODERATE', 'Moderate'),
        ('ELEVATED', 'Elevated'),
        ('HIGH', 'High / Clinically Significant'),
    ]

    assessment = models.ForeignKey(
        Assessment,
        on_delete=models.CASCADE,
        related_name='screening_results'
    )
    category = models.ForeignKey(
        QuestionnaireCategory,
        on_delete=models.CASCADE,
        related_name='screening_results'
    )
    raw_score = models.FloatField(default=0.0)
    max_score = models.FloatField(default=0.0)
    score_percentage = models.FloatField(default=0.0)
    severity_level = models.CharField(max_length=30, choices=SEVERITY_LEVELS, default='MINIMAL')
    is_elevated = models.BooleanField(default=False)
    indicator_summary = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'screening_results'
        unique_together = ('assessment', 'category')
        ordering = ['category__category_order']
        verbose_name = 'Screening Result'
        verbose_name_plural = 'Screening Results'

    def __str__(self):
        return f"Result #{self.assessment_id} {self.category.name}: {self.severity_level} ({self.raw_score}/{self.max_score})"

