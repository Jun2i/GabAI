from .models import Notification

def notifications_context(request):
    if request.user.is_authenticated:
        unread_notifications = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        )[:5]
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        urgent_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
            is_urgent=True
        ).count()
        return {
            'unread_notifications': unread_notifications,
            'unread_notifications_count': unread_count,
            'urgent_notifications_count': urgent_count,
        }
    return {
        'unread_notifications': [],
        'unread_notifications_count': 0,
        'urgent_notifications_count': 0,
    }

