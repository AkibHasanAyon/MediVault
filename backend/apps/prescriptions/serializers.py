from rest_framework import serializers
from .models import Prescription, PrescriptionMedication, DrugInteractionRule
from .services.interaction_service import DrugInteractionService
from .signals import sync_prescription_to_patient_roster

class PrescriptionMedicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionMedication
        fields = [
            'id',
            'brand_name',
            'generic_name',
            'dosage_form',
            'strength',
            'frequency',
            'timing_relation',
            'duration_days',
            'special_instructions',
        ]
        read_only_fields = ['id']


class PrescriptionDetailSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.user.full_name', read_only=True)
    doctor_bmdc = serializers.CharField(source='doctor.bmdc_number', read_only=True)
    doctor_specialties = serializers.CharField(source='doctor.specialties', read_only=True)
    patient_name = serializers.CharField(source='patient.user.full_name', read_only=True)
    family_member_name = serializers.CharField(source='family_member.full_name', read_only=True)
    clinic_name = serializers.CharField(source='clinic.name', read_only=True)
    medications = PrescriptionMedicationSerializer(many=True, read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            'id',
            'doctor',
            'doctor_name',
            'doctor_bmdc',
            'doctor_specialties',
            'patient',
            'patient_name',
            'family_member',
            'family_member_name',
            'clinic',
            'clinic_name',
            'chief_complaints',
            'clinical_findings',
            'diagnosis',
            'follow_up_date',
            'follow_up_notes',
            'medications',
            'pdf_url',
            'created_at',
        ]
        read_only_fields = ['id', 'doctor', 'created_at']

    def get_pdf_url(self, obj) -> str | None:
        if obj.pdf_file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.pdf_file.url)
            return obj.pdf_file.url
        return None


class PrescriptionCreateSerializer(serializers.ModelSerializer):
    medications = PrescriptionMedicationSerializer(many=True, required=True)
    clinical_override_notes = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = Prescription
        fields = [
            'id',
            'patient',
            'family_member',
            'clinic',
            'chief_complaints',
            'clinical_findings',
            'diagnosis',
            'follow_up_date',
            'follow_up_notes',
            'clinical_override_notes',
            'medications',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        meds = attrs.get('medications', [])
        if not meds:
            raise serializers.ValidationError({"medications": "Prescription must contain at least one medication."})

        # Run safety interaction check on generics
        generics = [m.get('generic_name') or m.get('brand_name') for m in meds if m.get('generic_name') or m.get('brand_name')]
        patient = attrs.get('patient')
        patient_id = str(patient.id) if patient else None

        interactions = DrugInteractionService.check_interactions(generics, patient_id=patient_id)
        has_contraindicated = any(i["severity"] == DrugInteractionRule.Severity.CONTRAINDICATED for i in interactions)

        override_note = attrs.get('clinical_override_notes', '').strip()
        if has_contraindicated and not override_note:
            contraindicated_pairs = [f"{i['drug_a']} + {i['drug_b']}" for i in interactions if i["severity"] == DrugInteractionRule.Severity.CONTRAINDICATED]
            raise serializers.ValidationError({
                "clinical_override_notes": f"Prescription includes CONTRAINDICATED drug pair(s): {', '.join(contraindicated_pairs)}. A clinical justification override note is required."
            })

        return attrs

    def create(self, validated_data):
        meds_data = validated_data.pop('medications')
        validated_data.pop('clinical_override_notes', None)

        request = self.context.get('request')
        if request and hasattr(request.user, 'doctor_profile'):
            validated_data['doctor'] = request.user.doctor_profile

        prescription = Prescription.objects.create(**validated_data)

        # Create nested medications
        for med_dict in meds_data:
            PrescriptionMedication.objects.create(prescription=prescription, **med_dict)

        # Trigger closed-loop sync to patient roster, reminders, follow-ups, and PDF
        sync_prescription_to_patient_roster(prescription)

        return prescription


class CheckInteractionInputSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField(required=False, allow_null=True)
    generics = serializers.ListField(
        child=serializers.CharField(max_length=150),
        allow_empty=False,
        required=True
    )

