import logging
from typing import List, Dict, Any
from django.db.models import Q
from .chroma_service import ChromaService
from apps.documents.models import MedicalDocument

logger = logging.getLogger('medivault.rag')

class RAGRetriever:
    """
    Retrieves clinically relevant document chunks scoped strictly to the requesting patient.
    Provides semantic vector retrieval via ChromaDB when online, with graceful fallback
    to database document search in development/offline modes.
    """

    def __init__(self):
        self.chroma = ChromaService()

    def retrieve_context(self, patient_id: str, query_text: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant chunks for a user query.
        Guarantees 100% patient isolation: documents from other patients are never returned.
        """
        if not patient_id:
            logger.warning("RAG retrieval rejected: patient_id is required.")
            return []

        retrieved_items = []

        # 1. Vector similarity search via ChromaDB (if online)
        try:
            chroma_docs = self.chroma.query_patient_records(patient_id=str(patient_id), query_text=query_text, n_results=top_k)
            for chunk in chroma_docs:
                if chunk and isinstance(chunk, str):
                    retrieved_items.append({
                        "document_id": None,
                        "title": "Uploaded Medical Record",
                        "date": None,
                        "type": "DOCUMENT",
                        "content": chunk
                    })
        except Exception as e:
            logger.warning("ChromaDB vector retrieval skipped: %s", str(e))

        # 2. Database Fallback (if Chroma returned no items or is offline)
        if not retrieved_items:
            logger.info("Retrieving patient documents from relational database for patient %s", patient_id)
            # Find documents matching keywords or retrieve recent verified documents
            keywords = [w.strip() for w in query_text.split() if len(w.strip()) > 3]
            query_filter = Q(patient_id=patient_id)

            if keywords:
                text_filter = Q()
                for kw in keywords[:3]:
                    text_filter |= Q(raw_ocr_text__icontains=kw) | Q(title__icontains=kw)
                doc_qs = MedicalDocument.objects.filter(query_filter & text_filter)
                if not doc_qs.exists():
                    doc_qs = MedicalDocument.objects.filter(query_filter)
            else:
                doc_qs = MedicalDocument.objects.filter(query_filter)

            docs = doc_qs.order_by('-document_date')[:top_k]
            for doc in docs:
                content = doc.raw_ocr_text if doc.raw_ocr_text else doc.title
                retrieved_items.append({
                    "document_id": str(doc.id),
                    "title": doc.title or f"{doc.document_type} ({doc.document_date})",
                    "date": str(doc.document_date),
                    "type": doc.document_type,
                    "content": content[:2500]
                })

        logger.info("RAGRetriever returned %d context chunks for patient %s", len(retrieved_items), patient_id)
        return retrieved_items

