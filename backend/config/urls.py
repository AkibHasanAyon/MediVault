"""
MediVault URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # Authentication & User Management
    path('api/v1/auth/', include('apps.accounts.urls', namespace='auth')),

    # Medical Document Management & OCR Ingestion
    path('api/v1/documents/', include('apps.documents.urls', namespace='documents')),

    # Daily Health Logs & Danger Alerts (Phase 4)
    path('api/v1/health-logs/', include('apps.health_logs.urls')),

    # Active Medications & Adherence Engine (Phase 4)
    path('api/v1/medications/', include('apps.medications.urls')),

    # AI Clinical Intelligence, RAG & Ask AI (Phase 5)
    path('api/v1/ai/', include('apps.ai_services.urls')),

    # Appointments & Pre-Intake Summaries (Phase 5)
    path('api/v1/appointments/', include('apps.appointments.urls')),

    # Doctor Pre-Consultation 10-Second Brief (Phase 5)
    path('api/v1/doctor/', include('apps.doctors.urls')),

    # Monthly Health Reports & Vector PDF (Phase 5)
    path('api/v1/reports/', include('apps.reports.urls')),

    # Ephemeral Scoped QR Consultation & Sharing (Phase 6)
    path('api/v1/sharing/', include('apps.sharing.urls')),

    # Digital Prescriptions & Drug Interactions (Phase 6)
    path('api/v1/prescriptions/', include('apps.prescriptions.urls')),

    # Interactive API Documentation (OpenAPI 3.1 & Swagger)
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
