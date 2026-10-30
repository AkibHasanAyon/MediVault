from django.urls import path
from .views.doctor_views import (
    DoctorLiveQueueView,
    DoctorCallNextView,
    DoctorStartConsultationView,
    DoctorFinishConsultationView,
    DoctorSkipPatientView,
)

urlpatterns = [
    path('live/', DoctorLiveQueueView.as_view(), name='doctor-queue-live'),
    path('call-next/', DoctorCallNextView.as_view(), name='doctor-queue-call-next'),
    path('<uuid:pk>/call-in/', DoctorCallNextView.as_view(), name='doctor-queue-call-in'),
    path('<uuid:pk>/start-consultation/', DoctorStartConsultationView.as_view(), name='doctor-queue-start-consultation'),
    path('<uuid:pk>/finish-consultation/', DoctorFinishConsultationView.as_view(), name='doctor-queue-finish-consultation'),
    path('<uuid:pk>/skip/', DoctorSkipPatientView.as_view(), name='doctor-queue-skip'),
]

