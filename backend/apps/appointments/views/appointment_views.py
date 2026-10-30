from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from ..models import Appointment, PreAppointmentSummary
from ..serializers import (
    AppointmentSerializer,
    PreAppointmentSummarySerializer,
    IntakeSubmissionSerializer,
)
from ..services.intake_synthesis import IntakeSynthesizer

class AppointmentViewSet(viewsets.ModelViewSet):
    """
    Manages patient chamber appointments and 3-question pre-appointment intake summaries.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'patient_profile'):
            return Appointment.objects.filter(patient=user.patient_profile).select_related('doctor__user', 'clinic', 'pre_summary')
        elif hasattr(user, 'doctor_profile'):
            return Appointment.objects.filter(doctor=user.doctor_profile).select_related('patient__user', 'clinic', 'pre_summary')
        return Appointment.objects.none()

    @action(detail=True, methods=['get', 'post'], url_path='pre-summary')
    def pre_summary(self, request, pk=None):
        appointment = self.get_object()

        if request.method == 'GET':
            if hasattr(appointment, 'pre_summary'):
                return Response({
                    "success": True,
                    "data": PreAppointmentSummarySerializer(appointment.pre_summary).data
                }, status=status.HTTP_200_OK)
            return Response({"error": "Pre-appointment summary has not been submitted yet."}, status=status.HTTP_404_NOT_FOUND)

        # POST: Submit 3-question intake
        serializer = IntakeSubmissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        summary = IntakeSynthesizer.synthesize_pre_appointment_brief(
            appointment=appointment,
            primary_concern=data['primary_concern'],
            reported_symptoms=data['reported_symptoms'],
            medication_side_effects=data.get('medication_side_effects', '')
        )

        return Response({
            "success": True,
            "message": "Intake questionnaire successfully synthesized for consulting doctor.",
            "data": PreAppointmentSummarySerializer(summary).data
        }, status=status.HTTP_201_CREATED)

