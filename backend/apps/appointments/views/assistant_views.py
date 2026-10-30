from datetime import datetime, date
from django.utils import timezone
from django.db.models import Max, Avg, F, ExpressionWrapper, fields, Count
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from apps.common.permissions import IsClinicAssistant
from apps.appointments.models import QueueEntry, Appointment
from apps.appointments.serializers import (
    QueueEntrySerializer,
    AssignTokenSerializer,
    QueueStatusUpdateSerializer,
)
from apps.appointments.consumers import broadcast_queue_event
from apps.clinics.models import Clinic
from apps.doctors.models import DoctorProfile
from apps.patients.models import PatientProfile, FamilyMember

User = get_user_model()


class AssignQueueTokenView(APIView):
    """
    POST /api/v1/assistant/queue/assign-token/
    Registers a walk-in or booked patient, generates daily sequential token (A-001, A-002),
    estimates wait time based on preceding queue length, and broadcasts WebSocket event.
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicAssistant]

    def post(self, request):
        serializer = AssignTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        patient_phone = data['patient_phone']
        patient_name = data.get('patient_name') or "Walk-in Patient"
        gender = data.get('gender', 'MALE')
        doctor_id = data['doctor_id']
        clinic_id = data.get('clinic_id')
        appointment_id = data.get('appointment_id')
        family_member_id = data.get('family_member_id')

        # 1. Resolve clinic
        if not clinic_id:
            if hasattr(request.user, 'assistant_profile'):
                clinic = request.user.assistant_profile.clinic
            else:
                # Fallback to doctor's primary clinic
                doctor = DoctorProfile.objects.get(id=doctor_id)
                assoc = doctor.clinic_associations.first()
                if assoc:
                    clinic = assoc.clinic
                else:
                    return Response({"error": "clinic_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                clinic = Clinic.objects.get(id=clinic_id)
            except Clinic.DoesNotExist:
                return Response({"error": "Clinic not found."}, status=status.HTTP_404_NOT_FOUND)

        # 2. Resolve doctor
        try:
            doctor = DoctorProfile.objects.select_related('user').get(id=doctor_id)
        except DoctorProfile.DoesNotExist:
            return Response({"error": "Doctor not found."}, status=status.HTTP_404_NOT_FOUND)

        # 3. Resolve or create Patient
        patient_user = User.objects.filter(phone_number=patient_phone).first()
        if not patient_user:
            patient_user = User.objects.create_user(
                phone_number=patient_phone,
                full_name=patient_name,
                role=User.Role.PATIENT,
            )
            # PatientProfile is auto-created by post_save signal
            patient_profile = patient_user.patient_profile
            patient_profile.gender = gender
            patient_profile.save(update_fields=['gender'])
        else:
            if not hasattr(patient_user, 'patient_profile'):
                patient_profile = PatientProfile.objects.create(
                    user=patient_user,
                    gender=gender,
                )
            else:
                patient_profile = patient_user.patient_profile

        # 4. Resolve Family Member if given
        family_member = None
        if family_member_id:
            family_member = FamilyMember.objects.filter(id=family_member_id, primary_account=patient_profile).first()

        # 5. Resolve Appointment if given
        appointment = None
        if appointment_id:
            appointment = Appointment.objects.filter(id=appointment_id).first()
            if appointment:
                appointment.status = Appointment.Status.ARRIVED
                appointment.save(update_fields=['status'])

        # 6. Generate sequential daily serial token
        today = timezone.localdate()
        max_token = QueueEntry.objects.filter(
            clinic=clinic,
            doctor=doctor,
            queue_date=today,
        ).aggregate(Max('token_number'))['token_number__max'] or 0

        next_token_number = max_token + 1

        # Calculate estimated wait time (7 mins per preceding waiting patient)
        waiting_count = QueueEntry.objects.filter(
            clinic=clinic,
            doctor=doctor,
            queue_date=today,
            state=QueueEntry.State.WAITING,
        ).count()
        estimated_wait_minutes = waiting_count * 7

        # 7. Create QueueEntry
        entry = QueueEntry.objects.create(
            clinic=clinic,
            doctor=doctor,
            patient=patient_profile,
            family_member=family_member,
            appointment=appointment,
            token_number=next_token_number,
            queue_date=today,
            state=QueueEntry.State.WAITING,
            estimated_wait_minutes=estimated_wait_minutes,
        )

        entry_data = QueueEntrySerializer(entry).data

        # 8. Broadcast TOKEN_ISSUED event via WebSocket
        broadcast_queue_event(
            clinic_id=clinic.id,
            event_type='TOKEN_ISSUED',
            data=entry_data,
            doctor_id=doctor.id,
        )

        return Response({
            "success": True,
            "message": f"Serial token {entry.token_display} issued successfully.",
            "data": entry_data,
            "position_in_queue": waiting_count + 1,
            "estimated_wait_minutes": estimated_wait_minutes,
        }, status=status.HTTP_201_CREATED)


class TodayQueueRosterView(APIView):
    """
    GET /api/v1/assistant/queue/today/
    Returns live roster of patients in chamber queue for today with status filters.
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicAssistant]

    def get(self, request):
        clinic_id = request.query_params.get('clinic_id')
        doctor_id = request.query_params.get('doctor_id')
        state_filter = request.query_params.get('state')
        date_param = request.query_params.get('date')

        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.localdate()
        else:
            target_date = timezone.localdate()

        if not clinic_id and hasattr(request.user, 'assistant_profile'):
            clinic_id = request.user.assistant_profile.clinic_id

        qs = QueueEntry.objects.filter(queue_date=target_date)

        if clinic_id:
            qs = qs.filter(clinic_id=clinic_id)
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)
        if state_filter:
            qs = qs.filter(state=state_filter)

        entries = qs.order_by('token_number').select_related(
            'clinic', 'doctor__user', 'patient__user', 'family_member', 'appointment'
        )

        serializer = QueueEntrySerializer(entries, many=True)
        return Response({
            "success": True,
            "count": entries.count(),
            "date": target_date.isoformat(),
            "data": serializer.data,
        }, status=status.HTTP_200_OK)


class UpdateQueueStatusView(APIView):
    """
    PATCH /api/v1/assistant/queue/{id}/status/
    Updates queue entry state (e.g. SKIPPED, WAITING, NO_SHOW).
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicAssistant]

    def patch(self, request, pk):
        try:
            entry = QueueEntry.objects.select_related('clinic', 'doctor__user', 'patient__user').get(id=pk)
        except QueueEntry.DoesNotExist:
            return Response({"error": "Queue entry not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = QueueStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_state = serializer.validated_data['state']

        entry.state = new_state
        if new_state == QueueEntry.State.CALLED_IN and not entry.called_at:
            entry.called_at = timezone.now()
        elif new_state == QueueEntry.State.DONE and not entry.completed_at:
            entry.completed_at = timezone.now()
        entry.save()

        entry_data = QueueEntrySerializer(entry).data

        event_name = 'PATIENT_SKIPPED' if new_state == QueueEntry.State.SKIPPED else 'QUEUE_STATUS_UPDATED'
        broadcast_queue_event(
            clinic_id=entry.clinic_id,
            event_type=event_name,
            data=entry_data,
            doctor_id=entry.doctor_id,
        )

        return Response({
            "success": True,
            "message": f"Queue status updated to {new_state}.",
            "data": entry_data,
        }, status=status.HTTP_200_OK)


class DailyQueueSummaryView(APIView):
    """
    GET /api/v1/assistant/queue/daily-summary/
    Aggregates end-of-day chamber queue metrics:
    - Registered vs seen
    - Average consultation and waiting times
    - No-show and cancellation rate
    """
    permission_classes = [permissions.IsAuthenticated, IsClinicAssistant]

    def get(self, request):
        clinic_id = request.query_params.get('clinic_id')
        doctor_id = request.query_params.get('doctor_id')
        date_param = request.query_params.get('date')

        if date_param:
            try:
                target_date = datetime.strptime(date_param, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.localdate()
        else:
            target_date = timezone.localdate()

        if not clinic_id and hasattr(request.user, 'assistant_profile'):
            clinic_id = request.user.assistant_profile.clinic_id

        qs = QueueEntry.objects.filter(queue_date=target_date)
        if clinic_id:
            qs = qs.filter(clinic_id=clinic_id)
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)

        total_registered = qs.count()
        total_completed = qs.filter(state=QueueEntry.State.DONE).count()
        total_waiting = qs.filter(state=QueueEntry.State.WAITING).count()
        total_in_chamber = qs.filter(state__in=[QueueEntry.State.CALLED_IN, QueueEntry.State.IN_CHAMBER]).count()
        total_skipped = qs.filter(state=QueueEntry.State.SKIPPED).count()
        total_no_show = qs.filter(state=QueueEntry.State.NO_SHOW).count()

        # Calculate average wait time (created_at -> called_at) in minutes
        called_entries = qs.filter(called_at__isnull=False)
        total_wait_seconds = 0
        wait_count = 0
        for e in called_entries:
            if e.called_at and e.created_at:
                diff = (e.called_at - e.created_at).total_seconds()
                if diff > 0:
                    total_wait_seconds += diff
                    wait_count += 1
        avg_wait_minutes = round((total_wait_seconds / wait_count) / 60, 1) if wait_count > 0 else 0.0

        # Calculate average consultation time (called_at -> completed_at) in minutes
        done_entries = qs.filter(called_at__isnull=False, completed_at__isnull=False)
        total_consult_seconds = 0
        consult_count = 0
        for e in done_entries:
            diff = (e.completed_at - e.called_at).total_seconds()
            if diff > 0:
                total_consult_seconds += diff
                consult_count += 1
        avg_consult_minutes = round((total_consult_seconds / consult_count) / 60, 1) if consult_count > 0 else 0.0

        no_show_rate = round((total_no_show / total_registered * 100), 1) if total_registered > 0 else 0.0

        return Response({
            "success": True,
            "date": target_date.isoformat(),
            "clinic_id": str(clinic_id) if clinic_id else None,
            "doctor_id": str(doctor_id) if doctor_id else None,
            "metrics": {
                "total_registered": total_registered,
                "total_completed": total_completed,
                "total_waiting": total_waiting,
                "total_in_chamber": total_in_chamber,
                "total_skipped": total_skipped,
                "total_no_show": total_no_show,
                "avg_wait_minutes": avg_wait_minutes,
                "avg_consultation_minutes": avg_consult_minutes,
                "no_show_rate_percent": no_show_rate,
            }
        }, status=status.HTTP_200_OK)

