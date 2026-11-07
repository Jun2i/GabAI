from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/patient/', views.register_patient_view, name='register_patient'),
    path('register/physician/', views.register_physician_view, name='register_physician'),
    path('consent/', views.privacy_consent_view, name='privacy_consent'),
    path('redirect/', views.dashboard_redirect_view, name='dashboard_redirect'),
    path('admin-portal/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-portal/physician/<int:physician_id>/verify/', views.verify_physician_view, name='verify_physician'),
]

