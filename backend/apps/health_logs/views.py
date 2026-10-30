from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from datetime import timedelta

from .models import (
    BloodGlucoseLog,
    BloodPressureLog,
    WeightLog,
    SymptomNote,
    DangerAlert,
)
from .serializers import (
    BloodGlucoseLogSerializer,
    BloodPressureLogSerializer,
    WeightLogSerializer,
    SymptomNoteSerializer,
    DangerAlertSerializer,
)
from apps.common.permissions import IsPatient, IsOwnerOrSharedDoctor

class BasePatientScopedViewSet(viewsets.ModelViewSet):
    """Base ViewSet ensuring data is scoped to the requesting patient and permitted family members."""
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'patient_profile'):
            return self.queryset.none()

        qs = self.queryset.filter(patient=user.patient_profile)
        family_member_id = self.request.query_params.get('family_member_id')
        if family_member_id:
            qs = qs.filter(family_member_id=family_member_id)

        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(recorded_at__date__gte=start_date)
        if end_date:
            qs = qs.filter(recorded_at__date__lte=end_date)

        return qs


class BloodGlucoseViewSet(BasePatientScopedViewSet):
    queryset = BloodGlucoseLog.objects.select_related('patient', 'family_member').all()
    serializer_class = BloodGlucoseLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        reading_type = self.request.query_params.get('reading_type')
        if reading_type:
            qs = qs.filter(reading_type=reading_type)
        return qs


class BloodPressureViewSet(BasePatientScopedViewSet):
    queryset = BloodPressureLog.objects.select_related('patient', 'family_member').all()
    serializer_class = BloodPressureLogSerializer


class WeightViewSet(BasePatientScopedViewSet):
    queryset = WeightLog.objects.select_related('patient', 'family_member').all()
    serializer_class = WeightLogSerializer


class SymptomNoteViewSet(BasePatientScopedViewSet):
    queryset = SymptomNote.objects.select_related('patient', 'family_member').all()
    serializer_class = SymptomNoteSerializer


class DangerAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """Lists danger alerts with immediate safety instructions and acknowledgment action."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = DangerAlertSerializer

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'patient_profile'):
            return DangerAlert.objects.none()

        qs = DangerAlert.objects.filter(patient=user.patient_profile)
        family_member_id = self.request.query_params.get('family_member_id')
        if family_member_id:
            qs = qs.filter(family_member_id=family_member_id)
        return qs

    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        alert = self.get_object()
        alert.is_acknowledged = True
        alert.save(update_fields=['is_acknowledged'])
        return Response({
            "success": True,
            "message": "Danger alert acknowledged by patient.",
            "data": DangerAlertSerializer(alert).data
        }, status=status.HTTP_200_OK)


class VitalsSummaryView(APIView):
    """
    Returns an aggregated overview of the patient's current vitals,
    latest readings, 7-day averages, and pending danger alerts.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not hasattr(user, 'patient_profile'):
            return Response({"error": "Only registered patients have health logs."}, status=status.HTTP_403_FORBIDDEN)

        patient = user.patient_profile
        family_member_id = request.query_params.get('family_member_id')

        glucose_qs = BloodGlucoseLog.objects.filter(patient=patient)
        bp_qs = BloodPressureLog.objects.filter(patient=patient)
        weight_qs = WeightLog.objects.filter(patient=patient)
        alert_qs = DangerAlert.objects.filter(patient=patient, is_acknowledged=False)

        if family_member_id:
            glucose_qs = glucose_qs.filter(family_member_id=family_member_id)
            bp_qs = bp_qs.filter(family_member_id=family_member_id)
            weight_qs = weight_qs.filter(family_member_id=family_member_id)
            alert_qs = alert_qs.filter(family_member_id=family_member_id)

        latest_glucose = glucose_qs.order_by('-recorded_at').first()
        latest_bp = bp_qs.order_by('-recorded_at').first()
        latest_weight = weight_qs.order_by('-recorded_at').first()

        # 7-day glucose average
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_glucose = glucose_qs.filter(recorded_at__gte=seven_days_ago)
        avg_glucose = None
        if recent_glucose.exists():
            from django.db.models import Avg
            avg = recent_glucose.aggregate(avg=Avg('glucose_value_mmol'))['avg']
            avg_glucose = round(float(avg), 1) if avg else None

        data = {
            "latest_glucose": BloodGlucoseLogSerializer(latest_glucose).data if latest_glucose else None,
            "seven_day_avg_glucose": avg_glucose,
            "latest_bp": BloodPressureLogSerializer(latest_bp).data if latest_bp else None,
            "latest_weight": WeightLogSerializer(latest_weight).data if latest_weight else None,
            "unacknowledged_danger_alerts_count": alert_qs.count(),
            "active_danger_alerts": DangerAlertSerializer(alert_qs[:5], many=True).data,
            "glucose": {
                "latest": BloodGlucoseLogSerializer(latest_glucose).data if latest_glucose else None,
                "avg_90_days": avg_glucose,
                "danger_count_30_days": alert_qs.count(),
            },
            "blood_pressure": {
                "latest": BloodPressureLogSerializer(latest_bp).data if latest_bp else None,
                "avg_systolic_90_days": None,
                "avg_diastolic_90_days": None,
                "crisis_count_30_days": 0,
            },
            "weight": {
                "latest": WeightLogSerializer(latest_weight).data if latest_weight else None,
                "current_bmi": round(float(latest_weight.calculated_bmi), 1) if latest_weight and latest_weight.calculated_bmi else None,
            },
        }
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

