from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    BloodGlucoseViewSet,
    BloodPressureViewSet,
    WeightViewSet,
    SymptomNoteViewSet,
    DangerAlertViewSet,
    VitalsSummaryView,
)

router = DefaultRouter()
router.register('blood-glucose', BloodGlucoseViewSet, basename='blood-glucose')
router.register('glucose', BloodGlucoseViewSet, basename='glucose')
router.register('blood-pressure', BloodPressureViewSet, basename='blood-pressure')
router.register('bp', BloodPressureViewSet, basename='bp')
router.register('weight', WeightViewSet, basename='weight')
router.register('symptoms', SymptomNoteViewSet, basename='symptoms')
router.register('danger-alerts', DangerAlertViewSet, basename='danger-alerts')

urlpatterns = [
    path('vitals/summary/', VitalsSummaryView.as_view(), name='vitals-summary-vitals'),
    path('summary/', VitalsSummaryView.as_view(), name='vitals-summary'),
    path('', include(router.urls)),
]
