from django.urls import path
from . import views

app_name = 'ai_engine'

urlpatterns = [
    path('chat/', views.chat_api_view, name='chat'),
]

