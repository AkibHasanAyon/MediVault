import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.accounts.models import User
from apps.patients.models import PatientProfile, FamilyMember
from apps.doctors.models import DoctorProfile
from apps.clinics.models import Clinic, ClinicAssistantProfile
from apps.health_logs.models import BloodGlucoseLog, BloodPressureLog, DangerAlert
from apps.documents.models import MedicalDocument, DocumentEntity
from apps.prescriptions.models import Prescription, PrescriptionMedication
from apps.medications.models import Medication, MedicationReminder, MedicationAdherence
from apps.appointments.models import Appointment, QueueEntry
from apps.sharing.models import ConsultationShare, ShareAuditLog

@pytest.mark.django_db
class TestPhase2CoreModels:

    def test_auto_profile_creation_signals(self):
        # Patient auto profile
        patient_user = User.objects.create_user(phone_number="+8801700000001", password="pwd", full_name="Patient One", role=User.Role.PATIENT)
        assert hasattr(patient_user, 'patient_profile')
        assert patient_user.patient_profile.known_allergies == "None reported"

        # Doctor auto profile
        doctor_user = User.objects.create_user(phone_number="+8801700000002", password="pwd", full_name="Doctor One", role=User.Role.DOCTOR)
        assert hasattr(doctor_user, 'doctor_profile')
        assert doctor_user.doctor_profile.primary_specialty == "General Practitioner"
        assert doctor_user.doctor_profile.is_verified_practitioner is False

    def test_family_member_eight_limit_constraint(self):
        patient_user = User.objects.create_user(phone_number="+8801700000003", password="pwd", full_name="Family Head")
        profile = patient_user.patient_profile

        # Create 8 family members successfully
        for i in range(1, 9):
            FamilyMember.objects.create(
                primary_account=profile,
                full_name=f"Member {i}",
                relationship=FamilyMember.Relationship.CHILD,
                gender=PatientProfile.Gender.MALE
            )

        assert profile.family_members.count() == 8

        # 9th family member must be rejected by clean()
        with pytest.raises(ValidationError) as exc_info:
            FamilyMember.objects.create(
                primary_account=profile,
                full_name="Member 9",
                relationship=FamilyMember.Relationship.OTHER,
                gender=PatientProfile.Gender.FEMALE
            )
        assert "cannot manage more than 8 family member profiles" in str(exc_info.value)

    def test_glucose_physiological_validation(self):
        patient_user = User.objects.create_user(phone_number="+8801700000004", password="pwd", full_name="Diabetic Patient")
        profile = patient_user.patient_profile

        # Valid entry
        log = BloodGlucoseLog(
            patient=profile,
            glucose_value_mmol=Decimal('5.8'),
            reading_type=BloodGlucoseLog.ReadingType.FASTING,
            recorded_at=timezone.now()
        )
        log.full_clean()
        log.save()
        assert log.id is not None

        # Typo: 99.0 mmol/L should be rejected
        with pytest.raises(ValidationError):
            invalid_log = BloodGlucoseLog(
                patient=profile,
                glucose_value_mmol=Decimal('99.0'),
                reading_type=BloodGlucoseLog.ReadingType.FASTING,
                recorded_at=timezone.now()
            )
            invalid_log.full_clean()

    def test_hypertensive_crisis_or_logic(self):
        patient_user = User.objects.create_user(phone_number="+8801700000005", password="pwd", full_name="BP Patient")
        profile = patient_user.patient_profile

        # Systolic > 180 but Diastolic <= 120 -> STILL A CRISIS
        bp1 = BloodPressureLog.objects.create(
            patient=profile,
            systolic_mmHg=185,
            diastolic_mmHg=90,
            recorded_at=timezone.now()
        )
        assert bp1.is_hypertensive_crisis is True

        # Systolic <= 180 but Diastolic > 120 -> STILL A CRISIS
        bp2 = BloodPressureLog.objects.create(
            patient=profile,
            systolic_mmHg=150,
            diastolic_mmHg=125,
            recorded_at=timezone.now()
        )
        assert bp2.is_hypertensive_crisis is True

        # Normal BP
        bp3 = BloodPressureLog.objects.create(
            patient=profile,
            systolic_mmHg=120,
            diastolic_mmHg=80,
            recorded_at=timezone.now()
        )
        assert bp3.is_hypertensive_crisis is False

    def test_soft_delete_lifecycle(self):
        clinic = Clinic.objects.create(name="Shapla Care", branch="Dhanmondi", address="Road 27", contact_phone="01711111111")
        assert Clinic.objects.count() == 1

        clinic.soft_delete()
        # Default objects manager filters out deleted
        assert Clinic.objects.count() == 0
        assert Clinic.all_objects.count() == 1
        assert Clinic.objects.deleted_only().count() == 1

        clinic.restore()
        assert Clinic.objects.count() == 1

    def test_prescription_and_medication_cascade(self):
        patient_user = User.objects.create_user(phone_number="+8801700000006", password="pwd", full_name="Rx Patient")
        doctor_user = User.objects.create_user(phone_number="+8801700000007", password="pwd", full_name="Rx Doctor", role=User.Role.DOCTOR)

        rx = Prescription.objects.create(
            doctor=doctor_user.doctor_profile,
            patient=patient_user.patient_profile,
            chief_complaints="Severe headache and high sugar",
            diagnosis="Type 2 Diabetes Mellitus"
        )
        med = PrescriptionMedication.objects.create(
            prescription=rx,
            brand_name="Nexum",
            strength="20mg",
            frequency="1+0+1"
        )
        assert rx.medications.count() == 1
        assert rx.medications.first().brand_name == "Nexum"

    def test_queue_entry_token_formatting(self):
        patient_user = User.objects.create_user(phone_number="+8801700000008", password="pwd", full_name="Queue Patient")
        doctor_user = User.objects.create_user(phone_number="+8801700000009", password="pwd", full_name="Queue Doctor", role=User.Role.DOCTOR)
        clinic = Clinic.objects.create(name="Popular Diagnostic", address="Panthapath", contact_phone="01722222222")

        entry = QueueEntry.objects.create(
            clinic=clinic,
            doctor=doctor_user.doctor_profile,
            patient=patient_user.patient_profile,
            token_number=14,
            queue_date=date.today()
        )
        assert entry.token_display == "A-014"
        assert entry.state == QueueEntry.State.WAITING

    def test_consultation_share_expiry(self):
        patient_user = User.objects.create_user(phone_number="+8801700000010", password="pwd", full_name="Share Patient")
        doctor_user = User.objects.create_user(phone_number="+8801700000011", password="pwd", full_name="Share Doctor", role=User.Role.DOCTOR)

        expires = timezone.now() + timedelta(minutes=30)
        share = ConsultationShare.objects.create(
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            token_hash="sample_hmac_hash_12345678",
            expires_at=expires
        )
        audit = ShareAuditLog.objects.create(
            share=share,
            doctor=doctor_user.doctor_profile,
            ip_address="192.168.1.1",
            action_summary="Scanned QR code and unlocked 30-min view"
        )
        assert share.is_active is True
        assert share.audit_logs.count() == 1

