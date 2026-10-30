from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    GenerateQRView,
    DoctorScanQRView,
    RevokeQRShareView,
    ConsultationShareViewSet,
)

router = DefaultRouter()
router.register('sessions', ConsultationShareViewSet, basename='sharing-sessions')

urlpatterns = [
    path('qr/generate/', GenerateQRView.as_view(), name='qr-generate'),
    path('scan/', DoctorScanQRView.as_view(), name='doctor-scan-qr'),
    path('<uuid:share_id>/revoke/', RevokeQRShareView.as_view(), name='share-revoke'),
    path('', include(router.urls)),
]

