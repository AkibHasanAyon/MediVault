import factory
from datetime import date, timedelta
from django.utils import timezone
from apps.accounts.models import User
from apps.patients.models import PatientProfile, FamilyMember
from apps.doctors.models import DoctorProfile
from apps.clinics.models import Clinic, ClinicAssistantProfile, ClinicDoctorAssociation
from apps.health_logs.models import BloodGlucoseLog, BloodPressureLog, WeightLog, SymptomNote
from apps.documents.models import MedicalDocument, DocumentEntity
from apps.prescriptions.models import Prescription, PrescriptionMedication
from apps.medications.models import Medication, MedicationReminder
from apps.appointments.models import Appointment, QueueEntry


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('phone_number',)

    phone_number = factory.Sequence(lambda n: f'+8801720{n:06d}')
    email = factory.LazyAttribute(lambda o: f'user_{o.phone_number.replace("+", "")}@medivault.app')
    full_name = factory.Sequence(lambda n: f'Test User {n}')
    role = User.Role.PATIENT
    is_phone_verified = True
    is_active = True


class DoctorUserFactory(UserFactory):
    role = User.Role.DOCTOR
    full_name = factory.Sequence(lambda n: f'Dr. Test Physician {n}')


class AssistantUserFactory(UserFactory):
    role = User.Role.ASSISTANT
    full_name = factory.Sequence(lambda n: f'Assistant Officer {n}')


class PatientProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PatientProfile
        django_get_or_create = ('user',)

    user = factory.SubFactory(UserFactory)
    date_of_birth = date(1990, 5, 15)
    gender = PatientProfile.Gender.MALE
    blood_group = PatientProfile.BloodGroup.B_POS
    emergency_contact_phone = '+8801700000000'
    known_allergies = "None reported"


class DoctorProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DoctorProfile
        django_get_or_create = ('user',)

    user = factory.SubFactory(DoctorUserFactory)
    bmdc_registration_number = factory.Sequence(lambda n: f'A-{n+50000}')
    degrees_qualifications = 'MBBS, FCPS (Medicine)'
    primary_specialty = 'Internal Medicine'
    consultation_fee = 1000.00
    chamber_address = 'Room 202, Medical Chamber'
    is_verified_practitioner = True


class ClinicFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Clinic

    name = factory.Sequence(lambda n: f'Central Diagnostic Lab {n}')
    branch = 'Dhaka Main Branch'
    address = 'Mirpur Road, Dhaka'
    contact_phone = '+8801700112233'
    is_active = True


class ClinicAssistantProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ClinicAssistantProfile

    user = factory.SubFactory(AssistantUserFactory)
    clinic = factory.SubFactory(ClinicFactory)
    desk_serial = 'Desk-A'
    is_active = True


class BloodGlucoseLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BloodGlucoseLog

    patient = factory.SubFactory(PatientProfileFactory)
    glucose_value_mmol = 5.6
    reading_type = BloodGlucoseLog.ReadingType.FASTING
    recorded_at = factory.LazyFunction(timezone.now)
    is_danger = False


class BloodPressureLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BloodPressureLog

    patient = factory.SubFactory(PatientProfileFactory)
    systolic_mmHg = 120
    diastolic_mmHg = 80
    pulse_bpm = 72
    recorded_at = factory.LazyFunction(timezone.now)
    is_danger = False


class WeightLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WeightLog

    patient = factory.SubFactory(PatientProfileFactory)
    weight_kg = 70.0
    height_cm = 175.0
    recorded_at = factory.LazyFunction(timezone.now)


class MedicalDocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MedicalDocument

    patient = factory.SubFactory(PatientProfileFactory)
    title = 'Routine Lab Chemistry'
    document_type = MedicalDocument.DocType.LAB_REPORT
    file = 'patient_documents/test_report.pdf'
    document_date = factory.LazyFunction(timezone.localdate)
    processing_status = MedicalDocument.ProcessingStatus.COMPLETED
    user_confirmed = True


class PrescriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Prescription

    doctor = factory.SubFactory(DoctorProfileFactory)
    patient = factory.SubFactory(PatientProfileFactory)
    clinic = factory.SubFactory(ClinicFactory)
    chief_complaints = 'Fever and headache'
    clinical_findings = 'Temp 100F, chest clear'
    diagnoses = factory.LazyFunction(lambda: ['Viral Fever'])
    general_advice = 'Rest and hydration'
    follow_up_advice = 'Review in 7 days'
    next_follow_up_date = factory.LazyFunction(lambda: timezone.localdate() + timedelta(days=7))


class QueueEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = QueueEntry

    clinic = factory.SubFactory(ClinicFactory)
    doctor = factory.SubFactory(DoctorProfileFactory)
    patient = factory.SubFactory(PatientProfileFactory)
    token_number = factory.Sequence(lambda n: n + 1)
    queue_date = factory.LazyFunction(timezone.localdate)
    state = QueueEntry.State.WAITING
    estimated_wait_minutes = 15
