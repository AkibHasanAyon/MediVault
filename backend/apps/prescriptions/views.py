import logging
from django.http import FileResponse, Http404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Prescription, DrugInteractionRule
from .serializers import (
    PrescriptionCreateSerializer,
    PrescriptionDetailSerializer,
    CheckInteractionInputSerializer,
)
from .services.interaction_service import DrugInteractionService
from .services.prescription_pdf import PrescriptionPDFBuilder

logger = logging.getLogger('medivault.prescriptions')

class PrescriptionViewSet(viewsets.ModelViewSet):
    """
    Digital Prescription Writer Canvas API & Safety Engine.
    - Doctors create and manage digital prescriptions with real-time drug interaction checks.
    - Patients view their received prescriptions and download clinic-branded PDFs.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return PrescriptionCreateSerializer
        return PrescriptionDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'doctor_profile'):
            return Prescription.objects.filter(doctor=user.doctor_profile).select_related(
                'patient__user', 'doctor__user', 'clinic', 'family_member'
            ).prefetch_related('medications')
        elif hasattr(user, 'patient_profile'):
            return Prescription.objects.filter(patient=user.patient_profile).select_related(
                'patient__user', 'doctor__user', 'clinic', 'family_member'
            ).prefetch_related('medications')
        return Prescription.objects.none()

    def create(self, request, *args, **kwargs):
        if not hasattr(request.user, 'doctor_profile'):
            return Response(
                {"error": "Only registered and verified doctors can issue digital prescriptions."},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        prescription = serializer.save()

        # Return full detail response
        detail_data = PrescriptionDetailSerializer(prescription, context={'request': request}).data
        return Response({
            "success": True,
            "message": "Digital prescription successfully created and synced to patient roster.",
            "data": detail_data
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'], url_path='pdf')
    def download_pdf(self, request, pk=None):
        """
        Streams the generated vector PDF of the prescription.
        """
        prescription = self.get_object()
        if not prescription.pdf_file:
            # Generate on the fly
            PrescriptionPDFBuilder.generate_pdf(prescription)
            prescription.refresh_from_db()

        if not prescription.pdf_file:
            raise Http404("Prescription PDF could not be generated.")

        return FileResponse(
            prescription.pdf_file.open('rb'),
            as_attachment=True,
            filename=f"Prescription_{prescription.id}_{prescription.created_at.strftime('%Y%m%d')}.pdf",
            content_type='application/pdf'
        )

    @action(detail=False, methods=['post'], url_path='check-interactions')
    def check_interactions(self, request):
        """
        POST /api/v1/prescriptions/check-interactions/
        Real-time clinical safety pre-check for drug-drug interactions.
        """
        serializer = CheckInteractionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        patient_id = str(data['patient_id']) if data.get('patient_id') else None
        generics = data['generics']

        interactions = DrugInteractionService.check_interactions(generics, patient_id=patient_id)
        has_contraindicated = any(i["severity"] == DrugInteractionRule.Severity.CONTRAINDICATED for i in interactions)
        has_severe = any(i["severity"] == DrugInteractionRule.Severity.SEVERE for i in interactions)

        return Response({
            "success": True,
            "interactions_count": len(interactions),
            "has_contraindicated": has_contraindicated,
            "has_severe": has_severe,
            "interactions": interactions
        }, status=status.HTTP_200_OK)

