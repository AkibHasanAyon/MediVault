from rest_framework import serializers
from django.utils import timezone
from .models import Medication, MedicationReminder, MedicationAdherence
from .services.schedule_builder import ScheduleBuilder

class MedicationReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicationReminder
        fields = ['id', 'reminder_time', 'label', 'is_enabled']


class MedicationSerializer(serializers.ModelSerializer):
    reminders = MedicationReminderSerializer(many=True, read_only=True)
    family_member_name = serializers.CharField(source='family_member.full_name', read_only=True)

    class Meta:
        model = Medication
        fields = [
            'id',
            'patient',
            'family_member',
            'family_member_name',
            'name',
            'generic_name',
            'strength',
            'dosage_pattern',
            'is_active',
            'start_date',
            'end_date',
            'refill_remaining_doses',
            'source_prescription',
            'provenance',
            'reminders',
            'created_at',
        ]
        read_only_fields = ['id', 'patient', 'created_at']

    def validate(self, attrs):
        request = self.context.get('request')
        if request and hasattr(request.user, 'patient_profile'):
            family_member = attrs.get('family_member')
            if family_member and family_member.primary_account != request.user.patient_profile:
                raise serializers.ValidationError({"family_member": "Selected family member does not belong to your account."})

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request.user, 'patient_profile'):
            validated_data['patient'] = request.user.patient_profile

        medication = super().create(validated_data)
        # Automatically generate default reminder times based on clinical dosage pattern (e.g. 1+0+1)
        ScheduleBuilder.generate_reminders_for_medication(medication)
        return medication


class MedicationAdherenceSerializer(serializers.ModelSerializer):
    medication_name = serializers.CharField(source='medication.name', read_only=True)
    strength = serializers.CharField(source='medication.strength', read_only=True)

    class Meta:
        model = MedicationAdherence
        fields = [
            'id',
            'medication',
            'medication_name',
            'strength',
            'reminder',
            'action',
            'scheduled_time',
            'recorded_time',
            'skip_reason',
        ]
        read_only_fields = ['id', 'recorded_time']


class RecordAdherenceInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=MedicationAdherence.Action.choices)
    scheduled_time = serializers.DateTimeField(required=False, default=timezone.now)
    reminder_id = serializers.UUIDField(required=False, allow_null=True)
    skip_reason = serializers.CharField(required=False, allow_blank=True, default="")

