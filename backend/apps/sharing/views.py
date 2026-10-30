import logging
from rest_framework import viewsets, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone

from .models import ConsultationShare, ShareAuditLog
from .serializers import (
    GenerateQRInputSerializer,
    ConsultationShareSerializer,
    ShareAuditLogSerializer,
    DoctorScanQRInputSerializer,
)
from .services.qr_service import QRSharingService
from .services.audit_service import AuditService
from apps.doctors.services.brief_service import DoctorBriefService
from apps.documents.models import MedicalDocument
from apps.medications.models import Medication
from apps.documents.serializers import MedicalDocumentTimelineSerializer
from apps.medications.serializers import MedicationSerializer

logger = logging.getLogger('medivault.sharing')

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class GenerateQRView(APIView):
    """
    POST /api/v1/sharing/qr/generate/
    Patient generates an ephemeral 30-minute QR code with scoped data permissions.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not hasattr(user, 'patient_profile'):
            return Response({"error": "Only registered patients can generate consultation QR shares."}, status=status.HTTP_403_FORBIDDEN)

        serializer = GenerateQRInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scope = serializer.validated_data

        share_result = QRSharingService.generate_qr_share(
            patient=user.patient_profile,
            scope=scope
        )

        return Response({
            "success": True,
            "message": "30-minute ephemeral consultation QR successfully generated.",
            "data": share_result
        }, status=status.HTTP_201_CREATED)


class DoctorScanQRView(APIView):
    """
    POST /api/v1/sharing/scan/
    POST /api/v1/doctor/consultation/scan-qr/
    Doctor scans patient QR code. Validates token, binds handshake, logs audit trail,
    and unlocks scoped clinical records and the 10-second brief.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not hasattr(user, 'doctor_profile'):
            return Response({"error": "Only verified doctors can scan patient consultation QR codes."}, status=status.HTTP_403_FORBIDDEN)

        serializer = DoctorScanQRInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        raw_token = serializer.validated_data['token']

        share = QRSharingService.validate_token(raw_token)
        if not share:
            return Response({
                "error": "Invalid, expired, or revoked consultation QR code. Please ask the patient to present a fresh QR code."
            }, status=status.HTTP_403_FORBIDDEN)

        doctor = user.doctor_profile

        # Bind doctor to share session
        share.doctor = doctor
        share.save(update_fields=['doctor'])

        # Write immutable audit log
        ip_addr = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        AuditService.log_access(
            share=share,
            doctor=doctor,
            ip_address=ip_addr,
            user_agent=user_agent,
            action_summary="Authorized consultation access via QR scan"
        )

        patient = share.patient
        scope = share.permitted_scope or {}

        # 1. 10-Second Doctor Brief
        brief_data = DoctorBriefService.get_patient_brief(str(patient.id))

        # 2. Scoped Documents
        docs_qs = MedicalDocument.objects.filter(patient=patient)
        if not scope.get('all_documents', True):
            specific_ids = scope.get('specific_document_ids', [])
            docs_qs = docs_qs.filter(id__in=specific_ids)
        documents_data = MedicalDocumentTimelineSerializer(docs_qs.order_by('-document_date')[:20], many=True).data

        # 3. Scoped Medications
        meds_data = []
        if scope.get('active_medications', True):
            meds_qs = Medication.objects.filter(patient=patient, is_active=True)
            meds_data = MedicationSerializer(meds_qs, many=True).data

        return Response({
            "success": True,
            "message": "Consultation handshake authorized.",
            "data": {
                "share_id": str(share.id),
                "expires_at": share.expires_at.isoformat(),
                "patient": {
                    "id": str(patient.id),
                    "name": patient.user.full_name,
                    "phone": patient.user.phone_number,
                    "blood_group": patient.blood_group,
                    "known_allergies": patient.known_allergies,
                    "height_cm": float(patient.height_cm) if patient.height_cm else None,
                },
                "ten_second_brief": brief_data,
                "permitted_documents": documents_data,
                "active_medications": meds_data,
                "permitted_scope": scope,
            }
        }, status=status.HTTP_200_OK)


class RevokeQRShareView(APIView):
    """
    POST/DELETE /api/v1/sharing/{id}/revoke/
    Patient revokes active doctor consultation access immediately.
    """
    permission_classes = [permissions.IsAuthenticated]

    def _revoke(self, request, share_id):
        user = request.user
        if not hasattr(user, 'patient_profile'):
            return Response({"error": "Only the owning patient can revoke a share."}, status=status.HTTP_403_FORBIDDEN)

        share = ConsultationShare.objects.filter(id=share_id, patient=user.patient_profile).first()
        if not share:
            return Response({"error": "Consultation share not found or already terminated."}, status=status.HTTP_404_NOT_FOUND)

        QRSharingService.revoke_share(share)

        return Response({
            "success": True,
            "message": "Consultation session revoked immediately. Doctor access has been terminated."
        }, status=status.HTTP_200_OK)

    def post(self, request, share_id):
        return self._revoke(request, share_id)

    def delete(self, request, share_id):
        return self._revoke(request, share_id)


class ConsultationShareViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Patient view of their active and historical consultation shares.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConsultationShareSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'patient_profile'):
            return ConsultationShare.objects.filter(patient=user.patient_profile).prefetch_related('audit_logs')
        elif hasattr(user, 'doctor_profile'):
            return ConsultationShare.objects.filter(doctor=user.doctor_profile).prefetch_related('audit_logs')
        return ConsultationShare.objects.none()

    @action(detail=False, methods=['get'], url_path='active')
    def active_shares(self, request):
        user = request.user
        if not hasattr(user, 'patient_profile'):
            return Response({"error": "Only patients have active consultation shares."}, status=status.HTTP_403_FORBIDDEN)

        qs = self.get_queryset().filter(is_active=True, expires_at__gt=timezone.now())
        return Response({
            "success": True,
            "count": qs.count(),
            "data": ConsultationShareSerializer(qs, many=True).data
        }, status=status.HTTP_200_OK)

