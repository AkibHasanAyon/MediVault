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

    # Interactive API Documentation (OpenAPI 3.1 & Swagger)
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
