from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from .models import MedicalDocument, DocumentEntity
from .serializers import (
    MedicalDocumentUploadSerializer,
    MedicalDocumentDetailSerializer,
    MedicalDocumentTimelineSerializer,
    DocumentReviewSerializer,
)
from .tasks import process_document_ocr_task
from apps.common.permissions import IsPatient, IsOwnerOrSharedDoctor

class MedicalDocumentViewSet(viewsets.ModelViewSet):
    """
    Medical Document Management & OCR Ingestion Pipeline.
    Supports camera photo / multi-page PDF upload, asynchronous OCR & AI entity parsing,
    side-by-side verification review, and chronological timeline filtering.
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrSharedDoctor]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'PATIENT' and hasattr(user, 'patient_profile'):
            return MedicalDocument.objects.filter(patient=user.patient_profile)
        elif user.role == 'DOCTOR' and hasattr(user, 'doctor_profile'):
            # Scoped to patients who have active sharing handshake with this doctor
            from apps.sharing.models import ConsultationShare
            from django.utils import timezone
            active_patient_ids = ConsultationShare.objects.filter(
                doctor=user.doctor_profile,
                is_active=True,
                expires_at__gt=timezone.now()
            ).values_list('patient_id', flat=True)
            return MedicalDocument.objects.filter(patient_id__in=active_patient_ids)
        return MedicalDocument.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return MedicalDocumentUploadSerializer
        elif self.action in ['timeline', 'list']:
            return MedicalDocumentTimelineSerializer
        elif self.action == 'review':
            return DocumentReviewSerializer
        return MedicalDocumentDetailSerializer

    @extend_schema(
        summary="Upload Medical Document",
        description="Ingests a medical document (JPEG, PNG, WebP, PDF up to 10MB) and triggers background OCR and clinical entity extraction.",
        responses={202: MedicalDocumentDetailSerializer}
    )
    def create(self, request, *args, **kwargs):
        if request.user.role != 'PATIENT':
            return Response(
                {"success": False, "message": "Only registered patient accounts can upload medical documents."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        doc = serializer.save()

        # Dispatch async Celery OCR task
        process_document_ocr_task.delay(str(doc.id))

        return Response(
            {
                "success": True,
                "message": "Document accepted for background OCR and entity extraction.",
                "data": {
                    "document_id": str(doc.id),
                    "status": doc.processing_status,
                    "document_type": doc.document_type,
                    "document_date": str(doc.document_date),
                    "file_url": request.build_absolute_uri(doc.file.url) if doc.file else None
                }
            },
            status=status.HTTP_202_ACCEPTED
        )

    @extend_schema(
        summary="Get Chronological Patient Timeline",
        parameters=[
            OpenApiParameter('document_type', str, description="Filter by DocType e.g. PRESCRIPTION, LAB_REPORT"),
            OpenApiParameter('family_member_id', str, description="Filter by Family Member UUID"),
            OpenApiParameter('start_date', str, description="Filter encounter dates on or after YYYY-MM-DD"),
            OpenApiParameter('end_date', str, description="Filter encounter dates on or before YYYY-MM-DD"),
        ],
        responses={200: MedicalDocumentTimelineSerializer(many=True)}
    )
    @action(detail=False, methods=['get'], url_path='timeline')
    def timeline(self, request):
        queryset = self.get_queryset()

        doc_type = request.query_params.get('document_type')
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)

        family_member_id = request.query_params.get('family_member_id')
        if family_member_id:
            queryset = queryset.filter(family_member_id=family_member_id)

        start_date = request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(document_date__gte=start_date)

        end_date = request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(document_date__lte=end_date)

        serializer = MedicalDocumentTimelineSerializer(queryset, many=True, context={'request': request})
        return Response({"success": True, "data": serializer.data})

    @extend_schema(
        summary="Review & Confirm Extracted Entities",
        description="Allows the patient to review side-by-side extraction, correct dosage/unit typos, and mark document as user confirmed.",
        request=DocumentReviewSerializer,
        responses={200: MedicalDocumentDetailSerializer}
    )
    @action(detail=True, methods=['put', 'patch'], url_path='review')
    def review(self, request, pk=None):
        doc = self.get_object()
        serializer = DocumentReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entities_payload = serializer.validated_data['entities']

        # Replace or update entities with user-confirmed provenance
        for item in entities_payload:
            entity_id = item.get('id')
            if entity_id:
                DocumentEntity.objects.filter(id=entity_id, document=doc).update(
                    entity_name=item['entity_name'],
                    entity_value=item.get('entity_value', ''),
                    unit=item.get('unit', ''),
                    reference_range=item.get('reference_range', ''),
                    is_abnormal=item.get('is_abnormal', False),
                    provenance=DocumentEntity.Provenance.PATIENT_CONFIRMED
                )
            else:
                DocumentEntity.objects.create(
                    document=doc,
                    entity_type=item['entity_type'],
                    entity_name=item['entity_name'],
                    entity_value=item.get('entity_value', ''),
                    unit=item.get('unit', ''),
                    reference_range=item.get('reference_range', ''),
                    is_abnormal=item.get('is_abnormal', False),
                    provenance=DocumentEntity.Provenance.PATIENT_CONFIRMED
                )

        doc.user_confirmed = True
        doc.save(update_fields=['user_confirmed'])

        detail_serializer = MedicalDocumentDetailSerializer(doc, context={'request': request})
        return Response(
            {
                "success": True,
                "message": "Extraction confirmed and verified by patient.",
                "data": detail_serializer.data
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm(self, request, pk=None):
        doc = self.get_object()
        doc.user_confirmed = True
        doc.save(update_fields=['user_confirmed'])
        doc.extracted_entities.update(provenance=DocumentEntity.Provenance.PATIENT_CONFIRMED)
        return Response({"success": True, "message": "Document marked as verified."})

