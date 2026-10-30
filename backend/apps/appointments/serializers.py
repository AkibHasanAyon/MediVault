import re
from rest_framework import serializers
from .models import Appointment, PreAppointmentSummary, QueueEntry
from apps.clinics.models import Clinic
from apps.doctors.models import DoctorProfile

class PreAppointmentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PreAppointmentSummary
        fields = [
            'id',
            'appointment',
            'primary_concern',
            'reported_symptoms',
            'medication_side_effects',
            'ai_synthesized_brief',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'ai_synthesized_brief', 'created_at', 'updated_at']


class IntakeSubmissionSerializer(serializers.Serializer):
    primary_concern = serializers.CharField(required=True, min_length=3)
    reported_symptoms = serializers.CharField(required=True, min_length=3)
    medication_side_effects = serializers.CharField(required=False, allow_blank=True, default="")


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.full_name', read_only=True)
    doctor_specialty = serializers.CharField(source='doctor.specialties', read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    pre_summary = PreAppointmentSummarySerializer(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id',
            'patient',
            'doctor',
            'doctor_name',
            'doctor_specialty',
            'clinic',
            'clinic_name',
            'scheduled_date',
            'slot_time',
            'status',
            'pre_summary',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class QueueEntrySerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.user.full_name', read_only=True)
    doctor_specialties = serializers.CharField(source='doctor.specialties', read_only=True)
    patient_name = serializers.CharField(source='patient.user.full_name', read_only=True)
    patient_phone = serializers.CharField(source='patient.user.phone_number', read_only=True)
    family_member_name = serializers.CharField(source='family_member.full_name', read_only=True, default=None)

    class Meta:
        model = QueueEntry
        fields = [
            'id',
            'clinic',
            'clinic_name',
            'doctor',
            'doctor_name',
            'doctor_specialties',
            'patient',
            'patient_name',
            'patient_phone',
            'family_member',
            'family_member_name',
            'appointment',
            'token_number',
            'token_display',
            'queue_date',
            'state',
            'estimated_wait_minutes',
            'called_at',
            'completed_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'token_number', 'token_display', 'created_at', 'updated_at']


class AssignTokenSerializer(serializers.Serializer):
    patient_phone = serializers.CharField(required=True)
    patient_name = serializers.CharField(required=False, allow_blank=True, default="Walk-in Patient")
    gender = serializers.ChoiceField(choices=['MALE', 'FEMALE', 'OTHER'], required=False, default='MALE')
    doctor_id = serializers.UUIDField(required=True)
    clinic_id = serializers.UUIDField(required=False, allow_null=True)
    appointment_id = serializers.UUIDField(required=False, allow_null=True)
    family_member_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_patient_phone(self, value):
        cleaned = re.sub(r'[\s\-]', '', value)
        if not re.match(r'^(?:\+8801|01)[3-9]\d{8}$', cleaned):
            raise serializers.ValidationError("Enter a valid Bangladesh mobile phone number (e.g. 01712345678 or +8801712345678).")
        # Standardize to international format
        if cleaned.startswith('01'):
            cleaned = '+88' + cleaned
        return cleaned


class QueueStatusUpdateSerializer(serializers.Serializer):
    state = serializers.ChoiceField(choices=QueueEntry.State.choices, required=True)


class DoctorCallNextSerializer(serializers.Serializer):
    entry_id = serializers.UUIDField(required=False, allow_null=True)
