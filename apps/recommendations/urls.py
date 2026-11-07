from django.urls import path
from . import views

app_name = 'recommendations'

urlpatterns = [
    path('review/<int:rec_id>/', views.review_recommendation_view, name='review'),
    path('patient/<int:rec_id>/', views.patient_recommendation_view, name='patient_view'),
    path('versions/<int:rec_id>/', views.version_history_view, name='version_history'),
]

