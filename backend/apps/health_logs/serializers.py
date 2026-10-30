from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers

from .models import (
    BloodGlucoseLog,
    BloodPressureLog,
    WeightLog,
    SymptomNote,
    DangerAlert,
)
from .validators import validate_glucose_value
from apps.patients.models import FamilyMember

class BloodGlucoseLogSerializer(serializers.ModelSerializer):
    recorded_at = serializers.DateTimeField(required=False, default=timezone.now)
    glucose_value_mmol = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        help_text="Glucose value in mmol/L"
    )
    # Optional input in mg/dL that auto-converts to mmol/L (mg/dL / 18.0182)
    glucose_value_mgdl = serializers.DecimalField(
        max_digits=5,
        decimal_places=1,
        required=False,
        write_only=True,
        help_text="Optional reading in mg/dL (auto-converts to mmol/L)"
    )
    family_member_name = serializers.CharField(source='family_member.full_name', read_only=True)

    class Meta:
        model = BloodGlucoseLog
        fields = [
            'id',
            'patient',
            'family_member',
            'family_member_name',
            'glucose_value_mmol',
            'glucose_value_mgdl',
            'reading_type',
            'recorded_at',
            'notes',
            'is_danger',
            'created_at',
        ]
        read_only_fields = ['id', 'patient', 'is_danger', 'created_at']

    def validate(self, attrs):
        # Auto-convert mg/dL to mmol/L if mmol is omitted but mg/dL is passed
        mgdl = attrs.pop('glucose_value_mgdl', None)
        if 'glucose_value_mmol' not in attrs and mgdl is not None:
            attrs['glucose_value_mmol'] = (Decimal(mgdl) / Decimal('18.0182')).quantize(Decimal('0.1'))

        if 'glucose_value_mmol' not in attrs:
            raise serializers.ValidationError({"glucose_value_mmol": "Glucose value is required (either in mmol/L or mg/dL)."})

        val = attrs.get('glucose_value_mmol')
        if val is not None:
            from django.core.exceptions import ValidationError as DjangoValidationError
            try:
                validate_glucose_value(val)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({"glucose_value_mmol": exc.message})

        if not attrs.get('recorded_at'):
            attrs['recorded_at'] = timezone.now()

        # Check family member ownership if provided
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
        return super().create(validated_data)


class BloodPressureLogSerializer(serializers.ModelSerializer):
    recorded_at = serializers.DateTimeField(required=False, default=timezone.now)
    family_member_name = serializers.CharField(source='family_member.full_name', read_only=True)
    bp_stage = serializers.SerializerMethodField()

    class Meta:
        model = BloodPressureLog
        fields = [
            'id',
            'patient',
            'family_member',
            'family_member_name',
            'systolic_mmHg',
            'diastolic_mmHg',
            'pulse_bpm',
            'recorded_at',
            'is_crisis',
            'bp_stage',
            'created_at',
        ]
        read_only_fields = ['id', 'patient', 'is_crisis', 'created_at']

    def get_bp_stage(self, obj) -> str:
        sys = obj.systolic_mmHg
        dia = obj.diastolic_mmHg

        if sys > 180 or dia > 120:
            return "HYPERTENSIVE_CRISIS"
        if sys >= 140 or dia >= 90:
            return "STAGE_2_HYPERTENSION"
        if (130 <= sys <= 139) or (80 <= dia <= 89):
            return "STAGE_1_HYPERTENSION"
        if 120 <= sys <= 129 and dia < 80:
            return "ELEVATED"
        return "NORMAL"

    def validate(self, attrs):
        if not attrs.get('recorded_at'):
            attrs['recorded_at'] = timezone.now()

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
        return super().create(validated_data)


class WeightLogSerializer(serializers.ModelSerializer):
    recorded_at = serializers.DateTimeField(required=False, default=timezone.now)
    family_member_name = serializers.CharField(source='family_member.full_name', read_only=True)

    class Meta:
        model = WeightLog
        fields = [
            'id',
            'patient',
            'family_member',
            'family_member_name',
            'weight_kg',
            'calculated_bmi',
            'recorded_at',
            'created_at',
        ]
        read_only_fields = ['id', 'patient', 'calculated_bmi', 'created_at']

    def validate(self, attrs):
        if not attrs.get('recorded_at'):
            attrs['recorded_at'] = timezone.now()

        request = self.context.get('request')
        if request and hasattr(request.user, 'patient_profile'):
            family_member = attrs.get('family_member')
            if family_member and family_member.primary_account != request.user.patient_profile:
                raise serializers.ValidationError({"family_member": "Selected family member does not belong to your account."})

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request.user, 'patient_profile'):
            patient = request.user.patient_profile
            validated_data['patient'] = patient
            # Compute BMI if patient profile has height_cm
            if patient.height_cm and patient.height_cm > 0:
                height_m = Decimal(patient.height_cm) / Decimal('100.0')
                bmi = Decimal(validated_data['weight_kg']) / (height_m * height_m)
                validated_data['calculated_bmi'] = bmi.quantize(Decimal('0.1'))

        return super().create(validated_data)


class SymptomNoteSerializer(serializers.ModelSerializer):
    recorded_at = serializers.DateTimeField(required=False, default=timezone.now)
    family_member_name = serializers.CharField(source='family_member.full_name', read_only=True)

    class Meta:
        model = SymptomNote
        fields = [
            'id',
            'patient',
            'family_member',
            'family_member_name',
            'symptom_tags',
            'severity',
            'notes',
            'onset_time',
            'recorded_at',
            'created_at',
        ]
        read_only_fields = ['id', 'patient', 'created_at']

    def validate(self, attrs):
        if not attrs.get('recorded_at'):
            attrs['recorded_at'] = timezone.now()

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
        return super().create(validated_data)


class DangerAlertSerializer(serializers.ModelSerializer):
    family_member_name = serializers.CharField(source='family_member.full_name', read_only=True)

    class Meta:
        model = DangerAlert
        fields = [
            'id',
            'patient',
            'family_member',
            'family_member_name',
            'alert_type',
            'trigger_value',
            'instruction_text',
            'is_acknowledged',
            'notification_dispatched',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'patient',
            'family_member',
            'alert_type',
            'trigger_value',
            'instruction_text',
            'notification_dispatched',
            'created_at',
        ]
