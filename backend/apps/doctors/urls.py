from django.urls import path
from .views import DoctorPatientBriefView

urlpatterns = [
    path('patients/<uuid:patient_id>/brief/', DoctorPatientBriefView.as_view(), name='doctor-patient-brief'),
]

