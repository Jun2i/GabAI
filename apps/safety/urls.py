from django.urls import path
from . import views

app_name = 'safety'

urlpatterns = [
    path('crisis-resources/', views.crisis_resources_view, name='crisis_resources'),
    path('emergency/', views.emergency_management_view, name='management'),
    path('emergency/<int:safety_id>/', views.emergency_detail_view, name='detail'),
]

