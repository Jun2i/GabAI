from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from django.conf import settings
from django.conf.urls.static import static

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard_redirect')
    return redirect('accounts:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', root_redirect, name='root'),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('patients/', include('apps.patients.urls', namespace='patients')),
    path('physicians/', include('apps.physicians.urls', namespace='physicians')),
    path('assessments/', include('apps.assessments.urls', namespace='assessments')),
    path('recommendations/', include('apps.recommendations.urls', namespace='recommendations')),
    path('wellness/', include('apps.wellness.urls', namespace='wellness')),
    path('safety/', include('apps.safety.urls', namespace='safety')),
    path('appointments/', include('apps.appointments.urls', namespace='appointments')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    path('ai/', include('apps.ai_engine.urls', namespace='ai_engine')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

