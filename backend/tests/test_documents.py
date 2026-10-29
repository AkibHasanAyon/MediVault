import io
import pytest
from datetime import date
from PIL import Image, ImageDraw
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.patients.models import PatientProfile
from apps.documents.models import MedicalDocument, DocumentEntity
from apps.documents.tasks import process_document_ocr_task
from apps.documents.validators import validate_medical_document_file
from django.core.exceptions import ValidationError

def create_valid_dummy_image():
    """Returns a valid JPEG image bytes with prescription text."""
    buf = io.BytesIO()
    img = Image.new("RGB", (350, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Dr. Nasreen Sultana MBBS", fill=(0, 0, 0))
    draw.text((10, 40), "Tab. Nexum 20mg 1+0+1 14 days", fill=(0, 0, 0))
    draw.text((10, 70), "Tab. Metfo 500mg 1+0+1 30 days", fill=(0, 0, 0))
    draw.text((10, 100), "Fasting Blood Glucose: 6.5 mmol/L", fill=(0, 0, 0))
    img.save(buf, format="JPEG")
    return buf.getvalue()

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestPhase3DocumentProcessing:

    def test_file_validator_guardrails(self):
        # 1. Valid JPEG file
        valid_file = SimpleUploadedFile("prescription.jpg", create_valid_dummy_image(), content_type="image/jpeg")
        validate_medical_document_file(valid_file)  # Should not raise

        # 2. File size exceeds 10MB
        oversized = SimpleUploadedFile("huge.jpg", b'\xff\xd8\xff' + (b'0' * (11 * 1024 * 1024)), content_type="image/jpeg")
        with pytest.raises(ValidationError) as exc:
            validate_medical_document_file(oversized)
        assert "exceeds maximum allowable limit of 10 MB" in str(exc.value)

        # 3. Spoofed extension: .jpg extension but text/exe header
        malicious = SimpleUploadedFile("virus.jpg", b'MZ\x90\x00executable', content_type="image/jpeg")
        with pytest.raises(ValidationError) as exc:
            validate_medical_document_file(malicious)
        assert "Invalid or corrupted file content" in str(exc.value)

    def test_document_upload_and_ocr_pipeline(self, api_client):
        patient_user = User.objects.create_user(phone_number="+8801720000001", password="pwd", full_name="Karim Ullah")
        api_client.force_authenticate(user=patient_user)

        # Upload valid prescription
        image_content = create_valid_dummy_image()
        upload_file = SimpleUploadedFile("rx_dr_nasreen.jpg", image_content, content_type="image/jpeg")

        payload = {
            "file": upload_file,
            "document_type": "PRESCRIPTION",
            "document_date": "2026-08-14",
            "title": "Evening Chamber Prescription"
        }
        res_upload = api_client.post('/api/v1/documents/upload/', data=payload, format='multipart')
        assert res_upload.status_code == 202
        assert res_upload.data["success"] is True
        doc_id = res_upload.data["data"]["document_id"]

        doc = MedicalDocument.objects.get(id=doc_id)
        # In eager mode (tests without live redis), Celery executes synchronously on .delay()
        if doc.processing_status != MedicalDocument.ProcessingStatus.COMPLETED:
            process_document_ocr_task(str(doc.id))
            doc.refresh_from_db()

        assert doc.processing_status == MedicalDocument.ProcessingStatus.COMPLETED
        assert len(doc.raw_ocr_text) > 0
        assert doc.chroma_vector_id != ""

        # Check extracted entities
        entities = doc.extracted_entities.all()
        assert entities.count() > 0

        # Check medications were extracted
        meds = entities.filter(entity_type=DocumentEntity.EntityType.MEDICATION)
        assert meds.exists()
        assert meds.filter(entity_name="Nexum").exists()

        # Check detail API
        res_detail = api_client.get(f'/api/v1/documents/{doc.id}/')
        assert res_detail.status_code == 200
        assert len(res_detail.data["extracted_entities"]) > 0

    def test_chronological_timeline_filtering(self, api_client):
        patient_user = User.objects.create_user(phone_number="+8801720000002", password="pwd", full_name="Timeline Patient")
        api_client.force_authenticate(user=patient_user)
        profile = patient_user.patient_profile

        # Create two documents with different dates
        img = create_valid_dummy_image()
        doc1 = MedicalDocument.objects.create(
            patient=profile,
            document_type=MedicalDocument.DocType.PRESCRIPTION,
            document_date=date(2026, 7, 10),
            title="July Rx",
            file=SimpleUploadedFile("doc1.jpg", img, content_type="image/jpeg")
        )
        doc2 = MedicalDocument.objects.create(
            patient=profile,
            document_type=MedicalDocument.DocType.LAB_REPORT,
            document_date=date(2026, 8, 20),
            title="August Lab",
            file=SimpleUploadedFile("doc2.jpg", img, content_type="image/jpeg")
        )

        # GET /api/v1/documents/timeline/
        res_timeline = api_client.get('/api/v1/documents/timeline/')
        assert res_timeline.status_code == 200
        data = res_timeline.data["data"]
        assert len(data) == 2
        # Newer date first
        assert data[0]["title"] == "August Lab"
        assert data[1]["title"] == "July Rx"

        # Filter by document_type=PRESCRIPTION
        res_filtered = api_client.get('/api/v1/documents/timeline/?document_type=PRESCRIPTION')
        assert res_filtered.status_code == 200
        assert len(res_filtered.data["data"]) == 1
        assert res_filtered.data["data"][0]["title"] == "July Rx"

    def test_patient_review_and_confirmation(self, api_client):
        patient_user = User.objects.create_user(phone_number="+8801720000003", password="pwd", full_name="Review Patient")
        api_client.force_authenticate(user=patient_user)
        profile = patient_user.patient_profile

        doc = MedicalDocument.objects.create(
            patient=profile,
            document_type=MedicalDocument.DocType.PRESCRIPTION,
            document_date=date(2026, 8, 1),
            file=SimpleUploadedFile("rx.jpg", create_valid_dummy_image(), content_type="image/jpeg")
        )
        entity = DocumentEntity.objects.create(
            document=doc,
            entity_type=DocumentEntity.EntityType.MEDICATION,
            entity_name="Metfo",
            entity_value="500mg - 1+0+1",
            provenance=DocumentEntity.Provenance.OCR_EXTRACTED
        )

        assert doc.user_confirmed is False

        # Review: Correct entity strength and confirm
        review_payload = {
            "entities": [
                {
                    "id": str(entity.id),
                    "entity_type": "MEDICATION",
                    "entity_name": "Metfo XR",
                    "entity_value": "850mg - 1+0+0",
                    "unit": "mg",
                    "is_abnormal": False
                }
            ]
        }
        res_review = api_client.put(f'/api/v1/documents/{doc.id}/review/', data=review_payload, format='json')
        assert res_review.status_code == 200
        assert res_review.data["success"] is True

        doc.refresh_from_db()
        assert doc.user_confirmed is True

        entity.refresh_from_db()
        assert entity.entity_name == "Metfo XR"
        assert entity.entity_value == "850mg - 1+0+0"
        assert entity.provenance == DocumentEntity.Provenance.PATIENT_CONFIRMED

    def test_unauthorized_patient_isolation(self, api_client):
        patient1 = User.objects.create_user(phone_number="+8801720000004", password="pwd", full_name="Patient One")
        patient2 = User.objects.create_user(phone_number="+8801720000005", password="pwd", full_name="Patient Two")

        doc = MedicalDocument.objects.create(
            patient=patient1.patient_profile,
            document_type=MedicalDocument.DocType.PRESCRIPTION,
            document_date=date(2026, 8, 1),
            file=SimpleUploadedFile("doc.jpg", create_valid_dummy_image(), content_type="image/jpeg")
        )

        # Patient 2 tries to access Patient 1's document
        api_client.force_authenticate(user=patient2)
        res = api_client.get(f'/api/v1/documents/{doc.id}/')
        assert res.status_code == 404
