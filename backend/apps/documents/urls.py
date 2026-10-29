from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicalDocumentViewSet

app_name = 'documents'

router = DefaultRouter()
router.register(r'', MedicalDocumentViewSet, basename='document')

urlpatterns = [
    # Support both /api/v1/documents/upload/ and /api/v1/documents/ for creation
    path('upload/', MedicalDocumentViewSet.as_view({'post': 'create'}), name='document-upload'),
    path('', include(router.urls)),
]

