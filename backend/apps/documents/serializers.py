from rest_framework import serializers
from .models import MedicalDocument, DocumentEntity
from apps.patients.models import FamilyMember
from .validators import validate_medical_document_file
from .utils import convert_heic_to_jpeg_if_needed

class DocumentEntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentEntity
        fields = (
            'id',
            'entity_type',
            'entity_name',
            'entity_value',
            'unit',
            'reference_range',
            'is_abnormal',
            'confidence_score',
            'provenance',
            'raw_snippet',
        )


class MedicalDocumentUploadSerializer(serializers.ModelSerializer):
    file = serializers.FileField(validators=[validate_medical_document_file], required=True)
    family_member_id = serializers.UUIDField(required=False, allow_null=True)
    document_type = serializers.ChoiceField(choices=MedicalDocument.DocType.choices, required=False, default=MedicalDocument.DocType.OTHER)
    document_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = MedicalDocument
        fields = (
            'id',
            'title',
            'document_type',
            'document_date',
            'file',
            'family_member_id',
            'issuing_doctor_name',
            'issuing_clinic_name',
            'processing_status',
            'created_at',
        )
        read_only_fields = ('id', 'processing_status', 'created_at')

    def validate_file(self, value):
        if value:
            return convert_heic_to_jpeg_if_needed(value)
        return value

    def validate_family_member_id(self, value):
        if value:
            request = self.context.get('request')
            patient_profile = request.user.patient_profile
            if not FamilyMember.objects.filter(id=value, primary_account=patient_profile).exists():
                raise serializers.ValidationError("Designated family member profile not found under your account.")
        return value

    def create(self, validated_data):
        family_member_id = validated_data.pop('family_member_id', None)
        family_member = None
        if family_member_id:
            family_member = FamilyMember.objects.get(id=family_member_id)

        request = self.context.get('request')
        patient_profile = request.user.patient_profile

        if 'document_date' not in validated_data or not validated_data['document_date']:
            from django.utils import timezone
            validated_data['document_date'] = timezone.now().date()

        if 'document_type' not in validated_data or not validated_data['document_type']:
            validated_data['document_type'] = MedicalDocument.DocType.OTHER

        document = MedicalDocument.objects.create(
            patient=patient_profile,
            family_member=family_member,
            processing_status=MedicalDocument.ProcessingStatus.PENDING,
            **validated_data
        )
        return document


class MedicalDocumentDetailSerializer(serializers.ModelSerializer):
    extracted_entities = DocumentEntitySerializer(many=True, read_only=True)
    file_url = serializers.SerializerMethodField()
    family_member_name = serializers.CharField(source='family_member.full_name', read_only=True, default=None)

    class Meta:
        model = MedicalDocument
        fields = (
            'id',
            'title',
            'document_type',
            'document_date',
            'file_url',
            'family_member',
            'family_member_name',
            'issuing_doctor_name',
            'issuing_clinic_name',
            'processing_status',
            'error_message',
            'user_confirmed',
            'raw_ocr_text',
            'extracted_entities',
            'created_at',
            'updated_at',
        )

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None


class MedicalDocumentTimelineSerializer(serializers.ModelSerializer):
    """Lightweight serializer for rapid chronological timeline feed."""
    file_url = serializers.SerializerMethodField()
    extracted_entities = DocumentEntitySerializer(many=True, read_only=True)
    medication_count = serializers.SerializerMethodField()
    lab_test_count = serializers.SerializerMethodField()
    diagnosis_count = serializers.SerializerMethodField()
    family_member_name = serializers.CharField(source='family_member.full_name', read_only=True, default=None)

    class Meta:
        model = MedicalDocument
        fields = (
            'id',
            'title',
            'document_type',
            'document_date',
            'file_url',
            'family_member_name',
            'issuing_doctor_name',
            'issuing_clinic_name',
            'processing_status',
            'error_message',
            'user_confirmed',
            'extracted_entities',
            'medication_count',
            'lab_test_count',
            'diagnosis_count',
            'created_at',
        )

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file:
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None

    def get_medication_count(self, obj):
        return obj.extracted_entities.filter(entity_type=DocumentEntity.EntityType.MEDICATION).count()

    def get_lab_test_count(self, obj):
        return obj.extracted_entities.filter(entity_type=DocumentEntity.EntityType.LAB_TEST).count()

    def get_diagnosis_count(self, obj):
        return obj.extracted_entities.filter(entity_type=DocumentEntity.EntityType.DIAGNOSIS).count()


class DocumentReviewItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(required=False, allow_null=True)
    entity_type = serializers.ChoiceField(choices=DocumentEntity.EntityType.choices)
    entity_name = serializers.CharField(max_length=255)
    entity_value = serializers.CharField(allow_blank=True, required=False, default="")
    unit = serializers.CharField(max_length=50, allow_blank=True, required=False, default="")
    reference_range = serializers.CharField(allow_blank=True, required=False, default="")
    is_abnormal = serializers.BooleanField(default=False)
    raw_snippet = serializers.CharField(allow_blank=True, required=False, default="")


class DocumentReviewSerializer(serializers.Serializer):
    """Serializer for patient confirming / correcting document metadata and extracted entities."""
    title = serializers.CharField(max_length=255, required=False, allow_blank=True)
    document_date = serializers.DateField(required=False, allow_null=True)
    document_type = serializers.ChoiceField(choices=MedicalDocument.DocType.choices, required=False)
    issuing_doctor_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    issuing_clinic_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    entities = DocumentReviewItemSerializer(many=True, required=False, default=list)

