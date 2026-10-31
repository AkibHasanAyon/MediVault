import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
import django
django.setup()
from apps.ai_services.models import AIConversation
from apps.documents.models import MedicalDocument, DocumentEntity

conv = AIConversation.objects.get(id="9531ec5a-84d5-441e-8b37-8e02dcbfd83b")
patient = conv.patient
print("Patient:", patient.user.full_name, patient.user.phone_number, "ID:", patient.id)
docs = MedicalDocument.objects.filter(patient=patient)
print("Docs count for patient:", docs.count())
for d in docs:
    print(f"Doc {d.id} | Title: {d.title} | Status: {d.processing_status} | OCR len: {len(d.raw_ocr_text or '')}")
    # Search for basophil in OCR
    ocr_lower = (d.raw_ocr_text or '').lower()
    if 'basophil' in ocr_lower or 'besophil' in ocr_lower:
        print("  --> Found basophil in OCR of doc", d.id)
        idx = ocr_lower.find('basophil')
        print("  --> Snippet:", d.raw_ocr_text[max(0, idx-50):idx+150])
    # Search in entities
    entities = d.extracted_entities.filter(entity_name__icontains='basophil')
    print("  --> Basophil entities:", list(entities.values('entity_name', 'entity_value', 'unit', 'reference_range')))

from apps.ai_services.rag_retriever import RAGRetriever
retriever = RAGRetriever()
chunks = retriever.retrieve_context(patient_id=str(patient.id), query_text="amr lab test report er besophil eta ki jinish? eta diye ki bujhi? r amr etar result kmn ashse?", top_k=4)
print("\n--- RAG RETRIEVED CHUNKS ---")
for c in chunks:
    print("Chunk doc_id:", c.get("document_id"), "Title:", c.get("title"))
    print("Content preview:", c.get("content")[:300])
    if "basophil" in (c.get("content") or '').lower():
        print("  --> CONTAINS BASOPHIL!")
    else:
        print("  --> DOES NOT CONTAIN BASOPHIL!")

