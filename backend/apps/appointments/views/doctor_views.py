from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.common.permissions import IsDoctor
from apps.appointments.models import QueueEntry
from apps.appointments.serializers import QueueEntrySerializer, DoctorCallNextSerializer
from apps.appointments.consumers import broadcast_queue_event
from apps.appointments.services.queue_notifier import QueueNotifierService


class DoctorLiveQueueView(APIView):
    """
    GET /api/v1/doctor/queue/live/
    Returns live in-chamber queue dashboard for consulting doctor:
    - Current patient in room (IN_CHAMBER)
    - Called patient arriving (CALLED_IN)
    - Next waiting patients
    - Today's chamber statistics
    """
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get(self, request):
        doctor = request.user.doctor_profile
        today = timezone.localdate()

        qs = QueueEntry.objects.filter(doctor=doctor, queue_date=today).select_related(
            'clinic', 'patient__user', 'family_member', 'appointment'
        )

        current_in_chamber = qs.filter(state=QueueEntry.State.IN_CHAMBER).first()
        called_patient = qs.filter(state=QueueEntry.State.CALLED_IN).first()
        next_waiting = qs.filter(state=QueueEntry.State.WAITING).order_by('token_number')[:5]

        return Response({
            "success": True,
            "date": today.isoformat(),
            "doctor_name": doctor.user.full_name,
            "current_patient": QueueEntrySerializer(current_in_chamber).data if current_in_chamber else None,
            "called_patient": QueueEntrySerializer(called_patient).data if called_patient else None,
            "next_waiting": QueueEntrySerializer(next_waiting, many=True).data,
            "stats": {
                "total_registered": qs.count(),
                "waiting_count": qs.filter(state=QueueEntry.State.WAITING).count(),
                "in_consultation": qs.filter(state__in=[QueueEntry.State.CALLED_IN, QueueEntry.State.IN_CHAMBER]).count(),
                "completed_count": qs.filter(state=QueueEntry.State.DONE).count(),
                "skipped_count": qs.filter(state=QueueEntry.State.SKIPPED).count(),
            }
        }, status=status.HTTP_200_OK)


class DoctorCallNextView(APIView):
    """
    POST /api/v1/doctor/queue/call-next/
    PUT /api/v1/doctor/queue/{id}/call-in/
    Doctor calls the next patient (or a specific serial) into the chamber.
    Updates status to CALLED_IN, records called_at, dispatches patient notification and proximity alerts,
    and broadcasts PATIENT_CALLED event via WebSocket.
    """
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request, pk=None):
        return self._handle_call(request, pk)

    def put(self, request, pk=None):
        return self._handle_call(request, pk)

    def _handle_call(self, request, pk=None):
        doctor = request.user.doctor_profile
        today = timezone.localdate()

        target_entry = None
        if pk:
            target_entry = QueueEntry.objects.filter(id=pk, doctor=doctor).first()
            if not target_entry:
                return Response({"error": "Queue entry not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            serializer = DoctorCallNextSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            entry_id = serializer.validated_data.get('entry_id')
            if entry_id:
                target_entry = QueueEntry.objects.filter(id=entry_id, doctor=doctor).first()
                if not target_entry:
                    return Response({"error": "Specified queue entry not found."}, status=status.HTTP_404_NOT_FOUND)
            else:
                # Find the next WAITING patient
                target_entry = QueueEntry.objects.filter(
                    doctor=doctor,
                    queue_date=today,
                    state=QueueEntry.State.WAITING,
                ).order_by('token_number').first()

        if not target_entry:
            return Response({
                "success": False,
                "message": "No patients currently waiting in line."
            }, status=status.HTTP_404_NOT_FOUND)

        # Update status to CALLED_IN
        target_entry.state = QueueEntry.State.CALLED_IN
        target_entry.called_at = timezone.now()
        target_entry.save(update_fields=['state', 'called_at'])

        entry_data = QueueEntrySerializer(target_entry).data

        # 1. Broadcast WebSocket event to clinic and doctor room
        broadcast_queue_event(
            clinic_id=target_entry.clinic_id,
            event_type='PATIENT_CALLED',
            data=entry_data,
            doctor_id=doctor.id,
        )

        # 2. Dispatch automated call-in alert to this patient
        QueueNotifierService.notify_patient_called(target_entry)

        # 3. Dispatch automated proximity alerts to upcoming waiting patients (e.g. 2 ahead)
        alerted_tokens = QueueNotifierService.notify_upcoming_patients(
            clinic_id=target_entry.clinic_id,
            doctor_id=doctor.id,
            current_queue_entry=target_entry,
            queue_date=today,
            target_ahead=2,
        )

        return Response({
            "success": True,
            "message": f"Called patient with token {target_entry.token_display}.",
            "data": entry_data,
            "upcoming_alerted_tokens": alerted_tokens,
        }, status=status.HTTP_200_OK)


class DoctorStartConsultationView(APIView):
    """
    POST /api/v1/doctor/queue/{id}/start-consultation/
    Updates status to IN_CHAMBER and broadcasts CONSULTATION_STARTED.
    """
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request, pk):
        doctor = request.user.doctor_profile
        try:
            entry = QueueEntry.objects.select_related('clinic', 'patient__user').get(id=pk, doctor=doctor)
        except QueueEntry.DoesNotExist:
            return Response({"error": "Queue entry not found."}, status=status.HTTP_404_NOT_FOUND)

        entry.state = QueueEntry.State.IN_CHAMBER
        entry.save(update_fields=['state'])

        entry_data = QueueEntrySerializer(entry).data
        broadcast_queue_event(
            clinic_id=entry.clinic_id,
            event_type='CONSULTATION_STARTED',
            data=entry_data,
            doctor_id=doctor.id,
        )

        return Response({
            "success": True,
            "message": f"Consultation started for token {entry.token_display}.",
            "data": entry_data,
        }, status=status.HTTP_200_OK)


class DoctorFinishConsultationView(APIView):
    """
    POST /api/v1/doctor/queue/{id}/finish-consultation/
    Marks consultation DONE, logs completed_at, and broadcasts CONSULTATION_ENDED.
    """
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request, pk):
        doctor = request.user.doctor_profile
        try:
            entry = QueueEntry.objects.select_related('clinic', 'patient__user').get(id=pk, doctor=doctor)
        except QueueEntry.DoesNotExist:
            return Response({"error": "Queue entry not found."}, status=status.HTTP_404_NOT_FOUND)

        entry.state = QueueEntry.State.DONE
        entry.completed_at = timezone.now()
        entry.save(update_fields=['state', 'completed_at'])

        entry_data = QueueEntrySerializer(entry).data
        broadcast_queue_event(
            clinic_id=entry.clinic_id,
            event_type='CONSULTATION_ENDED',
            data=entry_data,
            doctor_id=doctor.id,
        )

        return Response({
            "success": True,
            "message": f"Consultation completed for token {entry.token_display}.",
            "data": entry_data,
        }, status=status.HTTP_200_OK)


class DoctorSkipPatientView(APIView):
    """
    POST /api/v1/doctor/queue/{id}/skip/
    Marks patient as SKIPPED and broadcasts PATIENT_SKIPPED.
    """
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request, pk):
        doctor = request.user.doctor_profile
        try:
            entry = QueueEntry.objects.select_related('clinic', 'patient__user').get(id=pk, doctor=doctor)
        except QueueEntry.DoesNotExist:
            return Response({"error": "Queue entry not found."}, status=status.HTTP_404_NOT_FOUND)

        entry.state = QueueEntry.State.SKIPPED
        entry.save(update_fields=['state'])

        entry_data = QueueEntrySerializer(entry).data
        broadcast_queue_event(
            clinic_id=entry.clinic_id,
            event_type='PATIENT_SKIPPED',
            data=entry_data,
            doctor_id=doctor.id,
        )

        return Response({
            "success": True,
            "message": f"Patient with token {entry.token_display} skipped.",
            "data": entry_data,
        }, status=status.HTTP_200_OK)

