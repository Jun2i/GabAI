from django.urls import path
from . import views

app_name = 'assessments'

urlpatterns = [
    path('', views.assessment_intro_view, name='intro'),
    path('start/', views.start_assessment_view, name='start'),
    path('<int:assessment_id>/take/', views.take_assessment_view, name='take_assessment'),
    path('<int:assessment_id>/summary/', views.assessment_summary_view, name='summary'),
    path('history/', views.assessment_history_view, name='history'),
]

