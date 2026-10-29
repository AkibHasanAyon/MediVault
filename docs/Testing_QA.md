# MediVault — Testing & Quality Assurance (QA) Guide

> **Test Runner:** `pytest` with `pytest-django` and `pytest-asyncio`  
> **Fixture Factory:** `factory-boy`  
> **Mocking Library:** `unittest.mock` and `responses`  
> **Target Coverage:** Minimum 85% Code Coverage on Clinical Data Pipelines

---

## 1. Testing Strategy Overview

Because MediVault handles clinical records, automated verification is divided across five distinct test boundaries:

```mermaid
graph TD
    T1["Unit Tests<br/>(Models, Serializers, Threshold Math)"] --> T2["API Integration Tests<br/>(Django REST Framework Views & Auth)"]
    T2 --> T3["Async Pipeline Tests<br/>(Celery Tasks with Mocked AI/OCR)"]
    T3 --> T4["Real-Time Protocol Tests<br/>(WebSocket Consumer Channels)"]
    T4 --> T5["End-to-End User Flow Tests<br/>(Playwright / Cypress)"]
```

---

## 2. Test Configuration & Fixtures

### 2.1 Pytest Configuration (`backend/pytest.ini`)
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings.development
python_files = tests.py test_*.py *_tests.py
addopts = --nomigrations --cov=apps --cov-report=term-missing --cov-report=html
filterwarnings =
    ignore::DeprecationWarning
```

### 2.2 Reusable Fixtures & Factories (`apps/conftest.py`)
```python
import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.patients.models import PatientProfile
from apps.doctors.models import DoctorProfile
from apps.clinics.models import Clinic, ClinicAssistantProfile

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def patient_user(db):
    user = User.objects.create_user(
        phone_number="+8801711111111",
        password="TestPassword#123",
        full_name="Rafiqul Islam",
        role=User.Role.PATIENT,
        is_phone_verified=True
    )
    PatientProfile.objects.create(user=user)
    return user

@pytest.fixture
def doctor_user(db):
    user = User.objects.create_user(
        phone_number="+8801722222222",
        password="TestPassword#123",
        full_name="Prof. Dr. Nasreen Akhter",
        role=User.Role.DOCTOR,
        is_phone_verified=True
    )
    DoctorProfile.objects.create(
        user=user,
        bmdc_registration_number="A-45920",
        primary_specialty="Internal Medicine"
    )
    return user

@pytest.fixture
def assistant_user(db):
    user = User.objects.create_user(
        phone_number="+8801733333333",
        password="TestPassword#123",
        full_name="Kamrul Hasan",
        role=User.Role.ASSISTANT,
        is_phone_verified=True
    )
    clinic = Clinic.objects.create(
        name="Green Life Medical Chambers",
        address="Green Road, Dhaka",
        contact_phone="+88029661234"
    )
    ClinicAssistantProfile.objects.create(user=user, clinic=clinic)
    return user
```

---

## 3. Unit & Model Tests

### 3.1 Danger Alert Signal Test (`apps/health_logs/tests/test_danger_alerts.py`)
```python
import pytest
from decimal import Decimal
from django.utils import timezone
from apps.health_logs.models import BloodGlucoseLog, DangerAlert

@pytest.mark.django_db
class TestDangerAlertTrigger:
    def test_hypoglycemia_triggers_danger_alert(self, patient_user):
        """Verify that glucose < 3.9 mmol/L creates a critical DangerAlert record."""
        profile = patient_user.patient_profile

        log = BloodGlucoseLog.objects.create(
            patient=profile,
            glucose_value_mmol=Decimal('3.2'),
            reading_type=BloodGlucoseLog.ReadingType.FASTING,
            recorded_at=timezone.now()
        )

        assert log.is_danger is True
        alert = DangerAlert.objects.filter(patient=profile).first()
        assert alert is not None
        assert alert.alert_type == DangerAlert.AlertType.HYPOGLYCEMIA
        assert "3.2 mmol/L" in alert.trigger_value
        assert "Take 15g fast-acting sugar" in alert.instruction_text

    def test_normal_glucose_does_not_trigger_alert(self, patient_user):
        """Verify normal glucose reading does not produce false alerts."""
        profile = patient_user.patient_profile

        log = BloodGlucoseLog.objects.create(
            patient=profile,
            glucose_value_mmol=Decimal('5.8'),
            reading_type=BloodGlucoseLog.ReadingType.FASTING,
            recorded_at=timezone.now()
        )

        assert log.is_danger is False
        assert DangerAlert.objects.filter(patient=profile).count() == 0
```

---

## 4. API Endpoint Integration Tests

### 4.1 Authentication & Role Boundary Tests (`apps/accounts/tests/test_auth_api.py`)
```python
import pytest
from rest_framework import status

@pytest.mark.django_db
class TestAuthAPI:
    def test_user_registration_success(self, api_client):
        payload = {
            "phone_number": "+8801799999999",
            "password": "SecurePassword#2026",
            "full_name": "Test User",
            "role": "PATIENT"
        }
        res = api_client.post('/api/v1/auth/register/', payload)
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data['success'] is True
        assert res.data['data']['is_phone_verified'] is False

    def test_duplicate_phone_registration_rejected(self, api_client, patient_user):
        payload = {
            "phone_number": patient_user.phone_number,
            "password": "NewPassword#2026",
            "full_name": "Duplicate User",
            "role": "PATIENT"
        }
        res = api_client.post('/api/v1/auth/register/', payload)
        assert res.status_code == status.HTTP_400_BAD_REQUEST

    def test_patient_cannot_access_doctor_endpoints(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)
        res = api_client.get('/api/v1/doctor/queue/today/')
        assert res.status_code == status.HTTP_403_FORBIDDEN
```

### 4.2 QR Consultation Handshake Test (`apps/sharing/tests/test_sharing_api.py`)
```python
import pytest
from rest_framework import status

@pytest.mark.django_db
class TestConsultationHandshake:
    def test_full_qr_handshake_flow(self, api_client, patient_user, doctor_user):
        # 1. Patient generates QR token
        api_client.force_authenticate(user=patient_user)
        gen_res = api_client.post('/api/v1/sharing/qr/generate/', {"scope": "LAST_90_DAYS"})
        assert gen_res.status_code == status.HTTP_200_OK
        qr_token = gen_res.data['data']['token']

        # 2. Doctor scans QR code
        api_client.force_authenticate(user=doctor_user)
        scan_res = api_client.post('/api/v1/doctor/consultation/scan-qr/', {"qr_token": qr_token})
        assert scan_res.status_code == status.HTTP_200_OK
        assert scan_res.data['data']['patient']['full_name'] == "Rafiqul Islam"
        assert "ai_pre_consultation_brief" in scan_res.data['data']

        # 3. Doctor can now view patient's timeline
        patient_id = scan_res.data['data']['patient']['id']
        timeline_res = api_client.get(f'/api/v1/doctor/patients/{patient_id}/timeline/')
        assert timeline_res.status_code == status.HTTP_200_OK
```

---

## 5. Mocking Third-Party Services (GCP & OpenAI)

```python
import pytest
from unittest.mock import patch
from apps.documents.tasks import process_document_ocr_task
from apps.documents.models import MedicalDocument

@pytest.mark.django_db
@patch('apps.ai_services.ocr_service.OCRService.extract_text_from_image')
@patch('apps.ai_services.openai_service.OpenAIService.extract_clinical_entities')
def test_async_ocr_celery_task(mock_extract_entities, mock_ocr, patient_user, tmp_path):
    # Setup mocks
    mock_ocr.return_value = {
        "raw_text": "Tab. Metformin 500mg 1+0+1 after food for Type 2 Diabetes",
        "confidence": 0.95
    }
    mock_extract_entities.return_value = {
        "diagnoses": ["Type 2 Diabetes"],
        "medications": [
            {
                "brand_name": "Metformin",
                "strength": "500mg",
                "dosage_pattern": "1+0+1",
                "timing_relation": "After Food",
                "duration": "90 days"
            }
        ]
    }

    # Create dummy file & document
    test_file = tmp_path / "rx.jpg"
    test_file.write_bytes(b"dummy image bytes")

    doc = MedicalDocument.objects.create(
        patient=patient_user.patient_profile,
        document_type=MedicalDocument.DocType.PRESCRIPTION,
        document_date="2026-08-14",
        file=str(test_file)
    )

    # Execute task synchronously
    process_document_ocr_task(str(doc.id))

    doc.refresh_from_db()
    assert doc.processing_status == MedicalDocument.ProcessingStatus.COMPLETED
    assert doc.extracted_entities.count() == 2
```

---

## 6. Continuous Integration (GitHub Actions)

Workflow file: `.github/workflows/ci.yml`:

```yaml
name: MediVault CI Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  backend-test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: medivault_test
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
        ports:
          - 5432:5432
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r backend/requirements.txt

      - name: Run Pytest Suite
        env:
          DATABASE_URL: postgres://test_user:test_password@localhost:5432/medivault_test
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key-for-ci
          OPENAI_API_KEY: mock-test-key
        run: |
          cd backend
          pytest --cov=apps --cov-fail-under=80
```

