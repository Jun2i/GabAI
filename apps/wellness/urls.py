from django.urls import path
from . import views

app_name = 'wellness'

urlpatterns = [
    path('schedule/', views.schedule_view, name='schedule'),
    path('activity/<int:activity_id>/update/', views.update_activity_status_view, name='update_activity'),
    path('patient/<int:patient_id>/progress/', views.weekly_progress_summary_view, name='weekly_summary'),
]

