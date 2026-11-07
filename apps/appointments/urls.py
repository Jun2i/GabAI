from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('', views.appointment_list_view, name='list'),
    path('request/', views.request_appointment_view, name='request'),
    path('<int:apt_id>/', views.appointment_detail_view, name='detail'),
]

