from django.db import models
from django.conf import settings
from django.utils import timezone

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('SAFETY_ALERT', 'Urgent Safety / Crisis Alert'),
        ('RECOMMENDATION_APPROVED', 'Physician Approved Care Guidance'),
        ('RECOMMENDATION_MODIFIED', 'Modified Recommendation Approved'),
        ('RECOMMENDATION_HOLD', 'Further Clinical Assessment Requested'),
        ('RECOMMENDATION_REJECTED', 'Recommendation Requires Review'),
        ('APPOINTMENT_REQUESTED', 'New Appointment Request'),
        ('APPOINTMENT_CONFIRMED', 'Appointment Confirmed'),
        ('ASSESSMENT_READY', 'New Assessment Submitted for Review'),
        ('ACTIVITY_REMINDER', 'Daily Wellness Activity Reminder'),
        ('SYSTEM', 'System Notification'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES, default='SYSTEM')
    title = models.CharField(max_length=200)
    message = models.TextField()
    action_url = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False, db_index=True)
    is_urgent = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"[{self.get_notification_type_display()}] to {self.recipient.username}: {self.title}"

    @classmethod
    def send(cls, recipient, notification_type, title, message, action_url='', is_urgent=False):
        return cls.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            action_url=action_url,
            is_urgent=is_urgent
        )

