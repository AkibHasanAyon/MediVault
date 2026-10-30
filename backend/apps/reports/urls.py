from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MonthlyHealthReportViewSet

router = DefaultRouter()
router.register('', MonthlyHealthReportViewSet, basename='monthly-reports')

urlpatterns = [
    path('', include(router.urls)),
]

