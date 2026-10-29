from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel

class MedicalDocument(TimeStampedUUIDModel):
    class DocType(models.TextChoices):
        PRESCRIPTION = 'PRESCRIPTION', _('Prescription')
        LAB_REPORT = 'LAB_REPORT', _('Diagnostic Lab Report')
        RADIOLOGY = 'RADIOLOGY', _('Radiology / Imaging')
        DISCHARGE = 'DISCHARGE', _('Discharge Certificate')
        OTHER = 'OTHER', _('Other Health Document')

    class ProcessingStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        PROCESSING_OCR = 'PROCESSING_OCR', _('Processing OCR')
        EXTRACTING_AI = 'EXTRACTING_AI', _('Extracting Clinical Data')
        COMPLETED = 'COMPLETED', _('Extraction Completed')
        FAILED = 'FAILED', _('Processing Failed')

    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='documents')
    family_member = models.ForeignKey('patients.FamilyMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='documents')
    title = models.CharField(max_length=255, blank=True)
    document_type = models.CharField(max_length=30, choices=DocType.choices, default=DocType.PRESCRIPTION, db_index=True)
    file = models.FileField(upload_to='patient_documents/%Y/%m/')
    document_date = models.DateField(help_text=_("Original encounter date stated on the document (not upload time)"))
    issuing_doctor_name = models.CharField(max_length=255, blank=True)
    issuing_clinic_name = models.CharField(max_length=255, blank=True)

    # OCR & AI Outputs
    raw_ocr_text = models.TextField(blank=True)
    processing_status = models.CharField(max_length=20, choices=ProcessingStatus.choices, default=ProcessingStatus.PENDING, db_index=True)
    error_message = models.TextField(blank=True)
    chroma_vector_id = models.CharField(max_length=100, blank=True, db_index=True)
    user_confirmed = models.BooleanField(default=False, help_text=_("Indicates whether patient confirmed extracted entities"))

    class Meta:
        verbose_name = _('Medical Document')
        verbose_name_plural = _('Medical Documents')
        ordering = ['-document_date', '-created_at']
        indexes = [
            models.Index(fields=['patient', 'document_type', 'document_date']),
            models.Index(fields=['processing_status']),
        ]

    def __str__(self):
        target = self.family_member.full_name if self.family_member else self.patient.user.full_name
        return f"{self.get_document_type_display()} - {target} ({self.document_date})"


class DocumentEntity(TimeStampedUUIDModel):
    class EntityType(models.TextChoices):
        MEDICATION = 'MEDICATION', _('Medication')
        DIAGNOSIS = 'DIAGNOSIS', _('Diagnosis / Clinical Condition')
        LAB_TEST = 'LAB_TEST', _('Biomarker / Lab Result')
        ALLERGY = 'ALLERGY', _('Reported Allergy')
        ADVICE = 'ADVICE', _('Clinical Advice / Instruction')

    class Provenance(models.TextChoices):
        OCR_EXTRACTED = 'OCR_EXTRACTED', _('Extracted via OCR/AI')
        PATIENT_CONFIRMED = 'PATIENT_CONFIRMED', _('Confirmed by Patient')
        CLINICIAN_AUTHORED = 'CLINICIAN_AUTHORED', _('Clinician Authored')

    document = models.ForeignKey(MedicalDocument, on_delete=models.CASCADE, related_name='extracted_entities')
    entity_type = models.CharField(max_length=20, choices=EntityType.choices, db_index=True)
    entity_name = models.CharField(max_length=255)
    entity_value = models.CharField(max_length=255, blank=True, help_text=_("e.g. 7.2 mmol/L or 500mg"))
    unit = models.CharField(max_length=50, blank=True)
    reference_range = models.CharField(max_length=100, blank=True)
    is_abnormal = models.BooleanField(default=False)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    raw_snippet = models.TextField(blank=True)
    provenance = models.CharField(max_length=30, choices=Provenance.choices, default=Provenance.OCR_EXTRACTED)

    class Meta:
        verbose_name = _('Document Extracted Entity')
        verbose_name_plural = _('Document Extracted Entities')
        ordering = ['entity_type', 'entity_name']

    def __str__(self):
        return f"[{self.entity_type}] {self.entity_name}: {self.entity_value or 'N/A'}"

