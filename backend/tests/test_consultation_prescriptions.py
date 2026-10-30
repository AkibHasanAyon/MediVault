import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.patients.models import PatientProfile
from apps.doctors.models import DoctorProfile
from apps.clinics.models import Clinic
from apps.sharing.models import ConsultationShare, ShareAuditLog
from apps.prescriptions.models import Prescription, PrescriptionMedication, DrugInteractionRule
from apps.medications.models import Medication, MedicationReminder
from apps.appointments.models import FollowUpReminder
from apps.prescriptions.services.interaction_service import DrugInteractionService
from apps.prescriptions.tasks import dispatch_scheduled_follow_up_reminders

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def patient_user():
    user = User.objects.create_user(
        phone_number="+8801750000001",
        email="patient.share@example.com",
        password="secretpassword",
        full_name="Kazi Nazrul"
    )
    profile = user.patient_profile
    profile.date_of_birth = date(1985, 3, 20)
    profile.blood_group = "O+"
    profile.known_allergies = "None reported"
    profile.save()
    return user

@pytest.fixture
def doctor_user():
    user = User.objects.create_user(
        phone_number="+8801750000002",
        email="doctor.farhana@example.com",
        password="secretpassword",
        full_name="Dr. Farhana Ahmed",
        role=User.Role.DOCTOR
    )
    profile = user.doctor_profile
    profile.bmdc_number = "A-11223"
    profile.specialties = "Cardiology & Internal Medicine"
    profile.is_verified = True
    profile.save()
    return user

@pytest.fixture
def clinic():
    return Clinic.objects.create(
        name="Popular Chamber",
        branch="Dhanmondi Branch",
        address="House 16, Road 2, Dhanmondi, Dhaka",
        contact_phone="+8801750000003"
    )

@pytest.mark.django_db
class TestPhase6ConsultationAndPrescriptions:

    def test_ephemeral_qr_generation(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        res = api_client.post('/api/v1/sharing/qr/generate/', data={
            "all_documents": True,
            "vitals_90d": True,
            "active_medications": True
        })
        assert res.status_code == 201
        data = res.data["data"]
        assert "token" in data
        assert "share_id" in data
        assert "qr_base64" in data
        assert data["qr_base64"].startswith("data:image/png;base64,")
        assert data["expires_in_seconds"] == 1800

        # Verify DB record
        share = ConsultationShare.objects.get(id=data["share_id"])
        assert share.patient == patient_user.patient_profile
        assert share.is_active is True
        assert share.doctor is None

    def test_doctor_qr_scan_handshake_and_audit_log(self, api_client, patient_user, doctor_user):
        # 1. Patient generates QR
        api_client.force_authenticate(user=patient_user)
        res_gen = api_client.post('/api/v1/sharing/qr/generate/', data={"all_documents": True})
        raw_token = res_gen.data["data"]["token"]
        share_id = res_gen.data["data"]["share_id"]

        # 2. Doctor scans QR code via doctor consultation endpoint
        api_client.force_authenticate(user=doctor_user)
        res_scan = api_client.post('/api/v1/doctor/consultation/scan-qr/', data={"token": raw_token}, HTTP_USER_AGENT="MediVault-Doctor-iPad")
        assert res_scan.status_code == 200
        assert res_scan.data["success"] is True

        scan_data = res_scan.data["data"]
        assert scan_data["patient"]["name"] == "Kazi Nazrul"
        assert "ten_second_brief" in scan_data
        assert "permitted_documents" in scan_data

        # Verify share now bound to doctor
        share = ConsultationShare.objects.get(id=share_id)
        assert share.doctor == doctor_user.doctor_profile

        # Verify immutable audit log
        audit = ShareAuditLog.objects.filter(share=share).first()
        assert audit is not None
        assert audit.doctor == doctor_user.doctor_profile
        assert "Authorized consultation access" in audit.action_summary

    def test_patient_in_session_revocation(self, api_client, patient_user, doctor_user):
        # Patient generates QR
        api_client.force_authenticate(user=patient_user)
        res_gen = api_client.post('/api/v1/sharing/qr/generate/', data={"all_documents": True})
        raw_token = res_gen.data["data"]["token"]
        share_id = res_gen.data["data"]["share_id"]

        # Patient revokes access
        res_revoke = api_client.post(f'/api/v1/sharing/{share_id}/revoke/')
        assert res_revoke.status_code == 200
        assert res_revoke.data["success"] is True

        share = ConsultationShare.objects.get(id=share_id)
        assert share.is_active is False

        # Doctor attempts to scan revoked QR -> 403 Forbidden
        api_client.force_authenticate(user=doctor_user)
        res_scan_fail = api_client.post('/api/v1/doctor/consultation/scan-qr/', data={"token": raw_token})
        assert res_scan_fail.status_code == 403
        assert "revoked" in res_scan_fail.data["error"].lower()

    def test_real_time_drug_interaction_pre_check(self, api_client, doctor_user):
        api_client.force_authenticate(user=doctor_user)

        # 1. Metformin + Ciprofloxacin -> SEVERE
        res1 = api_client.post('/api/v1/prescriptions/check-interactions/', data={
            "generics": ["Metformin", "Ciprofloxacin"]
        })
        assert res1.status_code == 200
        assert res1.data["interactions_count"] >= 1
        interaction1 = res1.data["interactions"][0]
        assert interaction1["severity"] == DrugInteractionRule.Severity.SEVERE
        assert "hypoglycemia" in interaction1["clinical_effect"].lower()

        # 2. Aspirin + Warfarin -> CONTRAINDICATED
        res2 = api_client.post('/api/v1/prescriptions/check-interactions/', data={
            "generics": ["Aspirin", "Warfarin"]
        })
        assert res2.status_code == 200
        assert res2.data["has_contraindicated"] is True
        interaction2 = next(i for i in res2.data["interactions"] if i["severity"] == DrugInteractionRule.Severity.CONTRAINDICATED)
        assert "bleeding" in interaction2["clinical_effect"].lower() or "hemorrhage" in interaction2["clinical_effect"].lower()

    def test_digital_prescription_creation_and_closed_loop_sync(self, api_client, doctor_user, patient_user, clinic):
        api_client.force_authenticate(user=doctor_user)
        patient_id = patient_user.patient_profile.id

        follow_up_target = timezone.localdate() + timedelta(days=90)

        prescription_payload = {
            "patient": str(patient_id),
            "clinic": str(clinic.id),
            "chief_complaints": "Generalized body ache and elevated blood sugar levels",
            "clinical_findings": "BP 130/80 mmHg, Pulse 76 bpm. Chest clear.",
            "diagnosis": "Type 2 Diabetes Mellitus with Mild Dyslipidemia",
            "follow_up_date": str(follow_up_target),
            "follow_up_notes": "Return after 3 months with fasting lipid profile",
            "medications": [
                {
                    "brand_name": "Nexum",
                    "generic_name": "Esomeprazole",
                    "dosage_form": "Tablet",
                    "strength": "20mg",
                    "frequency": "1+0+1",
                    "timing_relation": "Before Food",
                    "duration_days": 14,
                    "special_instructions": "Take 30 mins before breakfast and dinner"
                },
                {
                    "brand_name": "Metfo XR",
                    "generic_name": "Metformin",
                    "dosage_form": "Tablet",
                    "strength": "500mg",
                    "frequency": "0+0+1",
                    "timing_relation": "After Food",
                    "duration_days": 90,
                    "special_instructions": "Take after dinner"
                }
            ]
        }

        res = api_client.post('/api/v1/doctor/prescriptions/', data=prescription_payload, format='json')
        assert res.status_code == 201
        rx_data = res.data["data"]
        rx_id = rx_data["id"]
        assert len(rx_data["medications"]) == 2

        # 1. Verify closed-loop sync to patient active medications
        active_meds = Medication.objects.filter(patient=patient_user.patient_profile, source_prescription_id=rx_id)
        assert active_meds.count() == 2
        nexum_med = active_meds.filter(name="Nexum").first()
        assert nexum_med is not None
        assert nexum_med.provenance == Medication.Provenance.CLINICIAN_AUTHORED

        # 2. Verify auto-generated reminders
        reminders = nexum_med.reminders.all()
        assert reminders.count() == 2  # 1+0+1 generates Morning + Night

        # 3. Verify auto-scheduled follow-up milestones
        follow_ups = FollowUpReminder.objects.filter(prescription_id=rx_id)
        assert follow_ups.count() >= 2  # 90 days ahead triggers 2.5 months, 1 week, and due date

        # 4. Verify generated PDF
        rx_obj = Prescription.objects.get(id=rx_id)
        assert rx_obj.pdf_file is not None

        res_pdf = api_client.get(f'/api/v1/prescriptions/{rx_id}/pdf/')
        assert res_pdf.status_code == 200
        assert res_pdf.headers["Content-Type"] == "application/pdf"
        assert len(res_pdf.getvalue()) > 500

    def test_contraindicated_prescription_requires_override_note(self, api_client, doctor_user, patient_user):
        api_client.force_authenticate(user=doctor_user)
        patient_id = patient_user.patient_profile.id

        # Prescribing Aspirin + Warfarin without override note must be rejected (400)
        payload = {
            "patient": str(patient_id),
            "chief_complaints": "DVT follow up",
            "diagnosis": "Atrial Fibrillation with CAD",
            "medications": [
                {
                    "brand_name": "Ecosprin",
                    "generic_name": "Aspirin",
                    "dosage_form": "Tablet",
                    "strength": "75mg",
                    "frequency": "0+1+0",
                    "duration_days": 30
                },
                {
                    "brand_name": "Marevan",
                    "generic_name": "Warfarin",
                    "dosage_form": "Tablet",
                    "strength": "5mg",
                    "frequency": "0+0+1",
                    "duration_days": 30
                }
            ]
        }
        res_fail = api_client.post('/api/v1/doctor/prescriptions/', data=payload, format='json')
        assert res_fail.status_code == 400
        assert "clinical_override_notes" in res_fail.data

        # Prescribing with explicit clinical override note must succeed
        payload["clinical_override_notes"] = "Patient with mechanical heart valve and recent coronary stent. Monitored with weekly INR target 2.0-2.5."
        res_success = api_client.post('/api/v1/doctor/prescriptions/', data=payload, format='json')
        assert res_success.status_code == 201

    def test_celery_follow_up_reminders_dispatcher(self, patient_user, doctor_user):
        # Create reminder due today
        rx = Prescription.objects.create(
            doctor=doctor_user.doctor_profile,
            patient=patient_user.patient_profile,
            chief_complaints="Routine checkup",
            diagnosis="Essential Hypertension",
            follow_up_date=timezone.localdate()
        )
        FollowUpReminder.objects.create(
            prescription=rx,
            patient=patient_user.patient_profile,
            doctor=doctor_user.doctor_profile,
            due_date=timezone.localdate(),
            milestone_stage=FollowUpReminder.Milestone.DUE_DATE,
            is_dispatched=False
        )

        # Trigger Celery task
        dispatched_count = dispatch_scheduled_follow_up_reminders()
        assert dispatched_count >= 1

