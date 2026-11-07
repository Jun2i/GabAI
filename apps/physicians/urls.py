from django.urls import path
from . import views

app_name = 'physicians'

urlpatterns = [
    path('dashboard/', views.physician_dashboard_view, name='dashboard'),
    path('patient/<int:patient_id>/', views.patient_clinical_detail_view, name='patient_detail'),
    path('patient/<int:patient_id>/record-clinical/', views.add_clinical_record_view, name='add_clinical_record'),
    path('patient/<int:patient_id>/schedule-followup/', views.schedule_follow_up_view, name='schedule_follow_up'),
]

