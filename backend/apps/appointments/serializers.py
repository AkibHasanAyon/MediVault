from rest_framework import serializers
from .models import Appointment, PreAppointmentSummary, QueueEntry

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

