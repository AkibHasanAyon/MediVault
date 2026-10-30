from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.appointments.models import QueueEntry
from apps.clinics.models import Clinic, ClinicDoctorAssociation


class ClinicQueueDisplayView(APIView):
    """
    GET /api/v1/queue/display/{clinic_id}/
    Public display endpoint designed for waiting room TV monitors / LED displays.
    Renders current serving token per doctor chamber and next 3 upcoming tokens.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, clinic_id):
        try:
            clinic = Clinic.objects.get(id=clinic_id)
        except Clinic.DoesNotExist:
            return Response({"error": "Clinic not found."}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.localdate()

        # Get all doctors associated with this clinic
        associations = ClinicDoctorAssociation.objects.filter(clinic=clinic).select_related('doctor__user')
        
        chambers = []
        for assoc in associations:
            doc = assoc.doctor
            qs = QueueEntry.objects.filter(
                clinic=clinic,
                doctor=doc,
                queue_date=today,
            ).order_by('token_number')

            current_entry = qs.filter(state__in=[QueueEntry.State.CALLED_IN, QueueEntry.State.IN_CHAMBER]).first()
            upcoming_entries = qs.filter(state=QueueEntry.State.WAITING)[:3]
            waiting_count = qs.filter(state=QueueEntry.State.WAITING).count()

            chambers.append({
                "doctor_id": str(doc.id),
                "doctor_name": doc.user.full_name,
                "specialties": doc.specialties,
                "chamber_number": assoc.chamber_number or "Chamber 1",
                "current_token": current_entry.token_display if current_entry else "--",
                "current_state": current_entry.state if current_entry else "IDLE",
                "upcoming_tokens": [e.token_display for e in upcoming_entries],
                "waiting_count": waiting_count,
            })

        return Response({
            "success": True,
            "clinic_name": clinic.name,
            "branch": clinic.branch,
            "date": today.isoformat(),
            "timestamp": timezone.now().isoformat(),
            "chambers": chambers,
        }, status=status.HTTP_200_OK)

