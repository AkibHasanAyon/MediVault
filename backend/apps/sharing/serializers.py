from rest_framework import serializers
from .models import ConsultationShare, ShareAuditLog

class GenerateQRInputSerializer(serializers.Serializer):
    all_documents = serializers.BooleanField(default=True)
    vitals_90d = serializers.BooleanField(default=True)
    active_medications = serializers.BooleanField(default=True)
    specific_document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list
    )
    family_member_id = serializers.UUIDField(required=False, allow_null=True)


class ShareAuditLogSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.full_name', read_only=True)
    doctor_bmdc = serializers.CharField(source='doctor.bmdc_number', read_only=True)

    class Meta:
        model = ShareAuditLog
        fields = [
            'id',
            'doctor_name',
            'doctor_bmdc',
            'ip_address',
            'user_agent',
            'action_summary',
            'created_at',
        ]


class ConsultationShareSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.full_name', read_only=True)
    doctor_bmdc = serializers.CharField(source='doctor.bmdc_number', read_only=True)
    patient_name = serializers.CharField(source='patient.user.full_name', read_only=True)
    audit_logs = ShareAuditLogSerializer(many=True, read_only=True)

    class Meta:
        model = ConsultationShare
        fields = [
            'id',
            'patient',
            'patient_name',
            'doctor',
            'doctor_name',
            'doctor_bmdc',
            'permitted_scope',
            'is_active',
            'expires_at',
            'audit_logs',
            'created_at',
        ]
        read_only_fields = ['id', 'patient', 'doctor', 'is_active', 'expires_at', 'created_at']


class DoctorScanQRInputSerializer(serializers.Serializer):
    token = serializers.CharField(required=True, max_length=255)

