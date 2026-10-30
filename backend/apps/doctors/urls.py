from django.urls import path, include
from .views import DoctorPatientBriefView
from apps.sharing.views import DoctorScanQRView

urlpatterns = [
    path('patients/<uuid:patient_id>/brief/', DoctorPatientBriefView.as_view(), name='doctor-patient-brief'),
    path('consultation/scan-qr/', DoctorScanQRView.as_view(), name='doctor-consultation-scan-qr'),
    path('prescriptions/', include('apps.prescriptions.urls')),
]
