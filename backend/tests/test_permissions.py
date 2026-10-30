import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import (
    UserFactory,
    PatientProfileFactory,
    DoctorProfileFactory,
    ClinicFactory,
    ClinicAssistantProfileFactory,
    MedicalDocumentFactory,
    BloodGlucoseLogFactory,
)
from apps.accounts.models import User
from apps.sharing.models import ConsultationShare


@pytest.mark.django_db
class TestPhase9RoleBasedAccessControlAndSecurity:

    @pytest.fixture(autouse=True)
    def setup_fixtures(self):
        self.clinic = ClinicFactory.create(name="Square Hospital Chamber")

        # Patients
        self.patient_user_a = UserFactory.create(role=User.Role.PATIENT)
        self.patient_profile_a = self.patient_user_a.patient_profile
        self.patient_jwt_a = str(RefreshToken.for_user(self.patient_user_a).access_token)

        self.patient_user_b = UserFactory.create(role=User.Role.PATIENT)
        self.patient_profile_b = self.patient_user_b.patient_profile
        self.patient_jwt_b = str(RefreshToken.for_user(self.patient_user_b).access_token)

        # Doctor
        self.doctor_user = UserFactory.create(role=User.Role.DOCTOR)
        self.doctor_profile = self.doctor_user.doctor_profile
        self.doctor_profile.is_verified_practitioner = True
        self.doctor_profile.bmdc_registration_number = "BMDC-99887"
        self.doctor_profile.primary_specialty = "Cardiology"
        self.doctor_profile.save()
        self.doctor_jwt = str(RefreshToken.for_user(self.doctor_user).access_token)

        # Assistant
        self.assistant_user = UserFactory.create(role=User.Role.ASSISTANT)
        self.assistant_profile = ClinicAssistantProfileFactory.create(
            user=self.assistant_user,
            clinic=self.clinic,
        )
        self.assistant_jwt = str(RefreshToken.for_user(self.assistant_user).access_token)

    def test_unauthenticated_requests_rejected(self):
        """Unauthenticated requests to protected endpoints must return 401 Unauthorized."""
        client = APIClient()

        # Vitals endpoint
        r1 = client.get('/api/v1/health-logs/summary/')
        assert r1.status_code == 401

        # Doctor queue endpoint
        r2 = client.get('/api/v1/doctor/queue/live/')
        assert r2.status_code == 401

        # Assistant desk endpoint
        r3 = client.get('/api/v1/assistant/queue/today/')
        assert r3.status_code == 401

    def test_patient_cannot_access_doctor_chamber_endpoints(self):
        """A patient account attempting to access doctor chamber endpoints is denied with 403 Forbidden."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.patient_jwt_a}")

        # Attempt to call in next patient
        res = client.post('/api/v1/doctor/queue/call-next/', {})
        assert res.status_code == 403

        # Attempt to access live queue
        res2 = client.get('/api/v1/doctor/queue/live/')
        assert res2.status_code == 403

        # Attempt to create prescription
        res3 = client.post('/api/v1/prescriptions/', {
            "patient_id": str(self.patient_profile_a.id),
            "chief_complaints": "Self prescribing",
            "diagnoses": ["Test"],
            "medications": [],
        })
        assert res3.status_code == 403

    def test_patient_cannot_access_assistant_queue_endpoints(self):
        """A patient account attempting to assign queue tokens is denied with 403 Forbidden."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.patient_jwt_a}")

        res = client.post('/api/v1/assistant/queue/assign-token/', {
            "patient_phone": "01711223344",
            "doctor_id": str(self.doctor_profile.id),
        })
        assert res.status_code == 403

    def test_assistant_cannot_write_prescriptions(self):
        """A clinic assistant attempting to write prescriptions is rejected with 403 Forbidden."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.assistant_jwt}")

        res = client.post('/api/v1/prescriptions/', {
            "patient_id": str(self.patient_profile_a.id),
            "chief_complaints": "Assistant prescribing",
            "diagnoses": ["None"],
            "medications": [],
        })
        assert res.status_code == 403

    def test_patient_cross_tenant_isolation(self):
        """Patient A cannot retrieve or modify Patient B's medical documents."""
        doc_b = MedicalDocumentFactory.create(patient=self.patient_profile_b, title="Private Report B")

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.patient_jwt_a}")

        # Patient A queries their own documents timeline
        res = client.get('/api/v1/documents/')
        assert res.status_code == 200
        items = res.data if isinstance(res.data, list) else res.data.get('results', [])
        doc_ids = [d['id'] for d in items]
        assert str(doc_b.id) not in doc_ids

        # Patient A directly requests Patient B's document ID
        res_direct = client.get(f'/api/v1/documents/{doc_b.id}/')
        assert res_direct.status_code in [403, 404]

    def test_shared_doctor_access_lifecycle(self):
        """
        A doctor can access patient records only when an active, non-expired ConsultationShare exists.
        Upon expiration or revocation, access is immediately blocked.
        """
        doc_a = MedicalDocumentFactory.create(patient=self.patient_profile_a, title="Cardiac Test A")

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.doctor_jwt}")

        # 1. Without active share -> 403/404
        r_unauth = client.get(f'/api/v1/documents/{doc_a.id}/')
        assert r_unauth.status_code in [403, 404]

        # 2. Patient creates consultation share with doctor
        share = ConsultationShare.objects.create(
            patient=self.patient_profile_a,
            doctor=self.doctor_profile,
            token_hash="sample_hash_token_123",
            expires_at=timezone.now() + timedelta(minutes=30),
            is_active=True,
        )

        # 3. Doctor now has object-level access via IsOwnerOrSharedDoctor
        r_auth = client.get(f'/api/v1/documents/{doc_a.id}/')
        assert r_auth.status_code == 200
        assert r_auth.data["id"] == str(doc_a.id)

        # 4. Patient revokes share -> doctor access immediately revoked
        share.is_active = False
        share.save()

        r_revoked = client.get(f'/api/v1/documents/{doc_a.id}/')
        assert r_revoked.status_code in [403, 404]
