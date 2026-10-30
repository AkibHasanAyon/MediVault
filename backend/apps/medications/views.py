from datetime import datetime, time
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Medication, MedicationReminder, MedicationAdherence
from .serializers import (
    MedicationSerializer,
    MedicationReminderSerializer,
    MedicationAdherenceSerializer,
    RecordAdherenceInputSerializer,
)
from .services.adherence import AdherenceEngine

class MedicationViewSet(viewsets.ModelViewSet):
    """
    Manages active medications, customized reminder alarms, daily dose logging,
    and adherence analytics.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = MedicationSerializer

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'patient_profile'):
            return Medication.objects.none()

        qs = Medication.objects.filter(patient=user.patient_profile).prefetch_related('reminders')
        family_member_id = self.request.query_params.get('family_member_id')
        if family_member_id:
            qs = qs.filter(family_member_id=family_member_id)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            active_bool = is_active.lower() in ['true', '1', 'yes']
            qs = qs.filter(is_active=active_bool)

        return qs

    @action(detail=True, methods=['post'], url_path='record-adherence')
    def record_adherence(self, request, pk=None):
        """
        Logs a dose action: TAKEN, SKIPPED, or SNOOZED.
        If TAKEN: automatically decrements refill remaining doses.
        If SKIPPED: enforces clinical safeguard note (zero catch-up dose).
        """
        medication = self.get_object()
        serializer = RecordAdherenceInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        action_val = data['action']
        scheduled_time = data.get('scheduled_time', timezone.now())
        reminder_id = data.get('reminder_id')
        skip_reason = data.get('skip_reason', '')

        reminder = None
        if reminder_id:
            reminder = MedicationReminder.objects.filter(id=reminder_id, medication=medication).first()

        adherence_entry = MedicationAdherence.objects.create(
            medication=medication,
            reminder=reminder,
            action=action_val,
            scheduled_time=scheduled_time,
            skip_reason=skip_reason
        )

        # On TAKEN: decrement remaining refills
        if action_val == MedicationAdherence.Action.TAKEN and medication.refill_remaining_doses > 0:
            medication.refill_remaining_doses -= 1
            medication.save(update_fields=['refill_remaining_doses'])

        response_data = {
            "success": True,
            "message": f"Dose successfully marked as {action_val}.",
            "adherence_log": MedicationAdherenceSerializer(adherence_entry).data,
            "refill_remaining_doses": medication.refill_remaining_doses,
        }

        if action_val == MedicationAdherence.Action.SKIPPED:
            response_data["clinical_safeguard"] = AdherenceEngine.SAFEGUARD_MISSED_DOSE_WARNING

        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='today')
    def today_schedule(self, request):
        """
        Returns all active medication reminder slots for today,
        annotated with whether each dose was TAKEN, SKIPPED, SNOOZED, or is still PENDING.
        """
        user = request.user
        if not hasattr(user, 'patient_profile'):
            return Response({"error": "Only registered patients have active medication schedules."}, status=status.HTTP_403_FORBIDDEN)

        patient = user.patient_profile
        today_date = timezone.localdate()

        active_meds = Medication.objects.filter(
            patient=patient,
            is_active=True
        ).prefetch_related('reminders')

        family_member_id = request.query_params.get('family_member_id')
        if family_member_id:
            active_meds = active_meds.filter(family_member_id=family_member_id)

        # Fetch today's adherence entries
        today_start = timezone.make_aware(datetime.combine(today_date, time.min))
        today_end = timezone.make_aware(datetime.combine(today_date, time.max))

        today_logs = MedicationAdherence.objects.filter(
            medication__in=active_meds,
            scheduled_time__range=(today_start, today_end)
        )
        logs_by_med_reminder = {}
        for log in today_logs:
            key = (str(log.medication_id), str(log.reminder_id) if log.reminder_id else None)
            logs_by_med_reminder[key] = log

        schedule_slots = []
        for med in active_meds:
            reminders = med.reminders.filter(is_enabled=True)
            for reminder in reminders:
                key = (str(med.id), str(reminder.id))
                logged = logs_by_med_reminder.get(key)
                status_val = logged.action if logged else "PENDING"

                schedule_slots.append({
                    "medication_id": str(med.id),
                    "medication_name": med.name,
                    "strength": med.strength,
                    "dosage_pattern": med.dosage_pattern,
                    "reminder_id": str(reminder.id),
                    "reminder_time": reminder.reminder_time.strftime('%I:%M %p'),
                    "raw_time": reminder.reminder_time.isoformat(),
                    "label": reminder.label,
                    "status": status_val,
                    "refill_remaining_doses": med.refill_remaining_doses,
                    "logged_at": logged.recorded_time.isoformat() if logged else None,
                })

        # Sort slots by raw_time
        schedule_slots.sort(key=lambda s: s['raw_time'])

        return Response({
            "success": True,
            "date": str(today_date),
            "total_doses": len(schedule_slots),
            "doses": schedule_slots
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='adherence-stats')
    def adherence_stats(self, request):
        """
        Returns adherence analytics (% taken, breakdown) over 30 days.
        """
        user = request.user
        if not hasattr(user, 'patient_profile'):
            return Response({"error": "Only registered patients have adherence analytics."}, status=status.HTTP_403_FORBIDDEN)

        days = int(request.query_params.get('days', 30))
        medication_id = request.query_params.get('medication_id')

        if medication_id:
            med = Medication.objects.filter(id=medication_id, patient=user.patient_profile).first()
            if not med:
                return Response({"error": "Medication not found."}, status=status.HTTP_404_NOT_FOUND)
            stats = AdherenceEngine.calculate_medication_adherence(med, days=days)
        else:
            stats = AdherenceEngine.calculate_overall_patient_adherence(user.patient_profile, days=days)

        return Response({"success": True, "data": stats}, status=status.HTTP_200_OK)

