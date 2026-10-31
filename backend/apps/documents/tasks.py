import sys
import logging
import threading
from celery import shared_task
from django.conf import settings
from .models import MedicalDocument, DocumentEntity
from apps.ai_services.ocr_service import OCRService
from apps.ai_services.openai_service import OpenAIService
from apps.ai_services.chroma_service import ChromaService

logger = logging.getLogger('medivault.documents')


def run_document_ocr_pipeline(document_id: str) -> bool:
    """
    Executes the 5-stage document OCR & AI clinical entity extraction pipeline:
    1. Status: PROCESSING_OCR -> OCR text extraction (Google Cloud Vision / local OCR).
    2. Status: EXTRACTING_AI -> OpenAI GPT-4o-mini structured clinical extraction.
    3. Ingestion: Saves medications, lab tests, and diagnoses as DocumentEntity rows.
    4. Indexing: ChromaDB cosine vector embedding & RAG retriever cache indexing.
    5. Status: COMPLETED.
    """
    logger.info("Starting background OCR & AI pipeline for document %s", document_id)
    try:
        doc = MedicalDocument.objects.get(id=document_id)
    except MedicalDocument.DoesNotExist:
        logger.error("MedicalDocument with id %s does not exist.", document_id)
        return False

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

        # Clear existing OCR-extracted entities if reprocessing/retrying
        doc.extracted_entities.filter(provenance=DocumentEntity.Provenance.OCR_EXTRACTED).delete()

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

        # 3.2 Ingest Lab Tests & Clinical Observations
        for lab in entities_data.get('lab_tests', []):
            test_name = lab.get('test_name') or 'Unnamed Lab Test'
            val = str(lab.get('observed_value') or '')
            unit = lab.get('unit') or ''
            ref_range = lab.get('reference_range') or ''
            is_abnormal = bool(lab.get('is_abnormal', False))
            source_page = lab.get('source_page')
            raw_snippet = f"[Page {source_page}] {test_name}: {val} {unit}".strip() if source_page else f"{test_name}: {val} {unit}".strip()

            DocumentEntity.objects.create(
                document=doc,
                entity_type=DocumentEntity.EntityType.LAB_TEST,
                entity_name=test_name,
                entity_value=val,
                unit=unit,
                reference_range=ref_range,
                is_abnormal=is_abnormal,
                raw_snippet=raw_snippet,
                provenance=DocumentEntity.Provenance.OCR_EXTRACTED
            )

        # 3.3 Ingest Diagnoses & Clinical Impressions
        for diag in entities_data.get('diagnoses', []):
            DocumentEntity.objects.create(
                document=doc,
                entity_type=DocumentEntity.EntityType.DIAGNOSIS,
                entity_name=str(diag),
                raw_snippet=str(diag),
                provenance=DocumentEntity.Provenance.OCR_EXTRACTED
            )

        # 3.4 Ingest Clinical Advice / Instructions
        if entities_data.get('follow_up_advice'):
            DocumentEntity.objects.create(
                document=doc,
                entity_type=DocumentEntity.EntityType.ADVICE,
                entity_name="Follow-up Clinical Advice",
                entity_value=str(entities_data['follow_up_advice']),
                raw_snippet=str(entities_data['follow_up_advice']),
                provenance=DocumentEntity.Provenance.OCR_EXTRACTED
            )

        # 3.5 Auto-classify document type, date, and smart title from AI extraction
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

        # Stage 4: Semantic Vector Indexing in ChromaDB & Local RAG Knowledgebase
        try:
            from apps.ai_services.rag_retriever import RAGRetriever
            RAGRetriever().index_document(doc)
        except Exception as rag_err:
            logger.warning("RAG indexing error: %s", str(rag_err))

        try:
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
        except Exception as chroma_err:
            logger.warning("Chroma indexing error: %s", str(chroma_err))

        # Stage 5: Mark Completed
        doc.processing_status = MedicalDocument.ProcessingStatus.COMPLETED
        doc.error_message = ""
        doc.save(update_fields=[
            'processing_status',
            'document_type',
            'document_date',
            'title',
            'issuing_doctor_name',
            'issuing_clinic_name',
            'chroma_vector_id',
            'error_message'
        ])
        logger.info("OCR & Entity Extraction pipeline finished successfully for document %s", document_id)
        return True

    except Exception as exc:
        logger.error("Error in OCR task for document %s: %s", document_id, str(exc))
        try:
            doc.processing_status = MedicalDocument.ProcessingStatus.FAILED
            doc.error_message = str(exc)
            doc.save(update_fields=['processing_status', 'error_message'])
        except Exception:
            pass
        return False


@shared_task(bind=True, max_retries=3)
def process_document_ocr_task(self, document_id: str):
    """
    Celery task wrapper around run_document_ocr_pipeline.
    """
    success = run_document_ocr_pipeline(document_id)
    if not success and hasattr(self, 'retry'):
        try:
            raise self.retry(countdown=15)
        except Exception:
            pass
    return success


def dispatch_document_processing(document_id: str):
    """
    Asynchronously dispatches document processing in the background.
    - If running under pytest/test runner: executes synchronously for deterministic testing.
    - If Celery broker is active & not in eager mode: dispatches to Celery.
    - Otherwise (e.g. local offline development / no Redis): dispatches to a background daemon thread
      so that the HTTP upload response returns immediately (in milliseconds).
    """
    is_testing = 'pytest' in sys.modules or any('pytest' in arg for arg in sys.argv) or 'test' in sys.argv
    if is_testing:
        run_document_ocr_pipeline(str(document_id))
        return

    is_eager = getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False)
    if not is_eager:
        try:
            process_document_ocr_task.delay(str(document_id))
            return
        except Exception as exc:
            logger.warning("Celery dispatch failed (%s), falling back to daemon thread.", exc)

    def _worker():
        from django.db import connection
        try:
            run_document_ocr_pipeline(str(document_id))
        except Exception as exc:
            logger.error("Background daemon thread failed for doc %s: %s", document_id, exc)
        finally:
            connection.close()

    thread = threading.Thread(
        target=_worker,
        name=f"bg-ocr-pipeline-{document_id}",
        daemon=True
    )
    thread.start()
