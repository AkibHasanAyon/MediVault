import logging
from celery import shared_task
from .models import MedicalDocument, DocumentEntity
from apps.ai_services.ocr_service import OCRService
from apps.ai_services.openai_service import OpenAIService
from apps.ai_services.chroma_service import ChromaService

logger = logging.getLogger('medivault.documents')

@shared_task(bind=True, max_retries=3)
def process_document_ocr_task(self, document_id: str):
    """
    Asynchronous Celery task orchestrating the complete 5-stage document pipeline:
    1. Status: PROCESSING_OCR -> Google Cloud Vision OCR detection.
    2. Status: EXTRACTING_AI -> OpenAI GPT-4o-mini structured clinical extraction.
    3. Ingestion: Saves medications, lab tests, and diagnoses as DocumentEntity rows.
    4. Indexing: ChromaDB cosine vector embedding.
    5. Status: COMPLETED.
    """
    logger.info("Starting background OCR & AI pipeline for document %s", document_id)
    try:
        doc = MedicalDocument.objects.get(id=document_id)
    except MedicalDocument.DoesNotExist:
        logger.error("MedicalDocument with id %s does not exist.", document_id)
        return

    try:
        # Stage 1: Google Cloud Vision OCR
        doc.processing_status = MedicalDocument.ProcessingStatus.PROCESSING_OCR
        doc.save(update_fields=['processing_status'])

        ocr_service = OCRService()
        file_path = doc.file.path if hasattr(doc.file, 'path') else str(doc.file)
        ocr_result = ocr_service.extract_text_from_image(file_path)
        doc.raw_ocr_text = ocr_result.get('raw_text', '')

        # Stage 2: OpenAI GPT-4o-mini Clinical Entity Extraction
        doc.processing_status = MedicalDocument.ProcessingStatus.EXTRACTING_AI
        doc.save(update_fields=['raw_ocr_text', 'processing_status'])

        ai_service = OpenAIService()
        entities_data = ai_service.extract_clinical_entities(doc.raw_ocr_text)

        # Stage 3: Ingest Structured Entities into DocumentEntity
        # 3.1 Ingest Medications
        for med in entities_data.get('medications', []):
            brand = med.get('brand_name') or 'Unnamed Medicine'
            strength = med.get('strength') or ''
            pattern = med.get('dosage_pattern') or ''
            timing = med.get('timing_relation') or ''
            value_str = f"{strength} {pattern}".strip()
            raw_snippet = f"{brand} {strength} {pattern} {timing}".strip()

            DocumentEntity.objects.create(
                document=doc,
                entity_type=DocumentEntity.EntityType.MEDICATION,
                entity_name=brand,
                entity_value=value_str,
                raw_snippet=raw_snippet,
                provenance=DocumentEntity.Provenance.OCR_EXTRACTED
            )

        # 3.2 Ingest Lab Tests
        for lab in entities_data.get('lab_tests', []):
            test_name = lab.get('test_name') or 'Unnamed Lab Test'
            val = str(lab.get('observed_value') or '')
            unit = lab.get('unit') or ''
            ref_range = lab.get('reference_range') or ''
            is_abnormal = bool(lab.get('is_abnormal', False))

            DocumentEntity.objects.create(
                document=doc,
                entity_type=DocumentEntity.EntityType.LAB_TEST,
                entity_name=test_name,
                entity_value=val,
                unit=unit,
                reference_range=ref_range,
                is_abnormal=is_abnormal,
                provenance=DocumentEntity.Provenance.OCR_EXTRACTED
            )

        # 3.3 Ingest Diagnoses
        for diag in entities_data.get('diagnoses', []):
            DocumentEntity.objects.create(
                document=doc,
                entity_type=DocumentEntity.EntityType.DIAGNOSIS,
                entity_name=str(diag),
                provenance=DocumentEntity.Provenance.OCR_EXTRACTED
            )

        # 3.4 Auto-classify document type, date, and smart title from AI extraction
        ai_doc_type = entities_data.get('document_type')
        if ai_doc_type:
            type_mapping = {
                'PRESCRIPTION': MedicalDocument.DocType.PRESCRIPTION,
                'LAB_REPORT': MedicalDocument.DocType.LAB_REPORT,
                'RADIOLOGY': MedicalDocument.DocType.RADIOLOGY,
                'DISCHARGE': MedicalDocument.DocType.DISCHARGE,
                'DISCHARGE_SUMMARY': MedicalDocument.DocType.DISCHARGE,
                'OTHER': MedicalDocument.DocType.OTHER,
            }
            matched_type = type_mapping.get(str(ai_doc_type).upper())
            if matched_type:
                doc.document_type = matched_type

        ai_doc_date = entities_data.get('document_date')
        if ai_doc_date:
            from datetime import datetime
            try:
                parsed_date = datetime.strptime(str(ai_doc_date)[:10], '%Y-%m-%d').date()
                doc.document_date = parsed_date
            except Exception:
                pass

        ai_title = entities_data.get('title')
        if ai_title and (not doc.title or doc.title in ['Medical Document', 'OTHER', 'PRESCRIPTION', 'LAB_REPORT']):
            doc.title = str(ai_title)[:255]

        # Optional Doctor / Clinic metadata enrichment
        if entities_data.get('doctor_name') and not doc.issuing_doctor_name:
            doc.issuing_doctor_name = entities_data['doctor_name']
        if entities_data.get('clinic_name') and not doc.issuing_clinic_name:
            doc.issuing_clinic_name = entities_data['clinic_name']

        # Stage 4: Semantic Vector Indexing in ChromaDB
        chroma = ChromaService()
        vector_id = chroma.index_document(
            doc_id=str(doc.id),
            patient_id=str(doc.patient.id),
            text=doc.raw_ocr_text,
            metadata={
                "document_date": str(doc.document_date),
                "document_type": doc.document_type,
                "title": doc.title or "Medical Document"
            }
        )
        doc.chroma_vector_id = vector_id

        # Stage 5: Mark Completed
        doc.processing_status = MedicalDocument.ProcessingStatus.COMPLETED
        doc.save(update_fields=[
            'processing_status',
            'document_type',
            'document_date',
            'title',
            'issuing_doctor_name',
            'issuing_clinic_name',
            'chroma_vector_id'
        ])
        logger.info("OCR & Entity Extraction pipeline finished successfully for document %s", document_id)

    except Exception as exc:
        logger.error("Error in OCR task for document %s: %s", document_id, str(exc))
        doc.processing_status = MedicalDocument.ProcessingStatus.FAILED
        doc.error_message = str(exc)
        doc.save(update_fields=['processing_status', 'error_message'])
        raise self.retry(exc=exc, countdown=15)

