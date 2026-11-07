from django.db import models
from django.utils import timezone
from datetime import date

class WellnessSchedule(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active Program'),
        ('COMPLETED', 'Completed'),
        ('ARCHIVED', 'Archived'),
    ]

    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='wellness_schedules'
    )
    recommendation = models.ForeignKey(
        'recommendations.AiRecommendation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedules'
    )
    title = models.CharField(max_length=200, default='Personalized Wellness Routine')
    start_date = models.DateField(default=date.today)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    is_physician_approved = models.BooleanField(
        default=False,
        help_text="Requires physician review before unlocking complete guidance"
    )
    custom_physician_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'wellness_schedules'
        ordering = ['-created_at']
        verbose_name = 'Wellness Schedule'
        verbose_name_plural = 'Wellness Schedules'

    def __str__(self):
        return f"{self.title} for {self.patient.user.get_full_name()} ({self.status})"


class WellnessActivity(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('SKIPPED', 'Skipped'),
        ('RESCHEDULED', 'Rescheduled'),
    ]

    ACTIVITY_CATEGORIES = [
        ('EXERCISE', 'Physical Exercise & Movement'),
        ('NUTRITION', 'Healthy Nutrition & Hydration'),
        ('WORK_BREAK', 'Work / Study Session with Break'),
        ('SOCIAL', 'Social & Family Interaction'),
        ('HOBBY', 'Personal Hobbies & Recreation'),
        ('JOURNALING', 'Journaling & Self-Reflection'),
        ('RELAXATION', 'Relaxation & Breathing Exercises'),
        ('SLEEP_HYGIENE', 'Sleep Hygiene & Bedtime Routine'),
        ('MINDFULNESS', 'Mindfulness & Grounding'),
    ]

    schedule = models.ForeignKey(
        WellnessSchedule,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='wellness_activities'
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=ACTIVITY_CATEGORIES, default='MINDFULNESS')
    scheduled_date = models.DateField(default=date.today)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    purpose = models.CharField(
        max_length=255,
        help_text="Clinical/wellness purpose (e.g. Circadian rhythm stabilization, Cortisol reduction)"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    is_weekly = models.BooleanField(
        default=False,
        help_text="True if this is a weekly milestone activity rather than daily"
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    patient_notes = models.TextField(blank=True, null=True, help_text="Patient thoughts or reflections")
    order = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = 'wellness_activities'
        ordering = ['scheduled_date', 'start_time', 'order']
        verbose_name = 'Wellness Activity'
        verbose_name_plural = 'Wellness Activities'

    def __str__(self):
        return f"[{self.status}] {self.title} ({self.scheduled_date} {self.start_time or ''})"


class ActivityProgress(models.Model):
    patient = models.ForeignKey(
        'patients.PatientProfile',
        on_delete=models.CASCADE,
        related_name='activity_progress_reports'
    )
    week_start_date = models.DateField()
    total_scheduled = models.PositiveIntegerField(default=0)
    total_completed = models.PositiveIntegerField(default=0)
    total_skipped = models.PositiveIntegerField(default=0)
    completion_percentage = models.FloatField(default=0.0)
    streak_days = models.PositiveIntegerField(default=0)
    weekly_reflection_notes = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        'physicians.PhysicianProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_progress_reports'
    )
    physician_feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'activity_progress'
        unique_together = ('patient', 'week_start_date')
        ordering = ['-week_start_date']
        verbose_name = 'Activity Progress'
        verbose_name_plural = 'Activity Progress Records'

    def __str__(self):
        return f"Progress for {self.patient.user.get_full_name()} (Week {self.week_start_date}): {self.completion_percentage:.1f}%"

