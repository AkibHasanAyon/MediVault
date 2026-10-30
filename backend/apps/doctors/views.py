from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response

from .services.brief_service import DoctorBriefService

class DoctorPatientBriefView(APIView):
    """
    10-Second Pre-Consultation Patient Summary.
    Delivers a sub-second cached synthesis of the patient's 90-day vital stability,
    active medication roster, danger alerts, and 3-bullet AI summary.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, patient_id):
        force_refresh = request.query_params.get('refresh', 'false').lower() == 'true'
        brief = DoctorBriefService.get_patient_brief(patient_id=str(patient_id), force_refresh=force_refresh)

        if "error" in brief:
            return Response({"error": brief["error"]}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "success": True,
            "data": brief
        }, status=status.HTTP_200_OK)

