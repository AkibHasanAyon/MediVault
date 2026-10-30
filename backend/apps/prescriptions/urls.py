from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PrescriptionViewSet

router = DefaultRouter()
router.register('', PrescriptionViewSet, basename='prescriptions')

urlpatterns = [
    path('', include(router.urls)),
]

