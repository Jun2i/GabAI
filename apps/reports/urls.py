from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('screening/<int:assessment_id>/', views.screening_report_view, name='screening_report'),
    path('recommendation/<int:rec_id>/', views.recommendation_report_view, name='recommendation_report'),
    path('analytics/', views.clinical_analytics_view, name='analytics'),
    path('audit-logs/', views.audit_log_view, name='audit_logs'),
]

