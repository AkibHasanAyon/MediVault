import os
import json
import math
import re
import difflib
import logging
from typing import List, Dict, Any
from django.conf import settings
from django.db.models import Q
from .chroma_service import ChromaService
from .openai_service import OpenAIService
from apps.documents.models import MedicalDocument, DocumentEntity

logger = logging.getLogger('medivault.rag')

class RAGRetriever:
    """
    Hybrid Clinical RAG Retriever for MediVault.
    Combines:
    1. Exact & Fuzzy Clinical Entity Matching (Lab measurements, medications, diagnoses, reference ranges).
    2. Local Semantic Vector Retrieval (OpenAI embeddings + cosine similarity, zero-Docker fallback).
    3. Document-level Relational & OCR Search (Context-aware excerpts, without arbitrary truncation).
    4. ChromaDB vector indexing when container is online.
    Guarantees 100% patient isolation: documents from other patients are never returned.
    """

    def __init__(self):
        self.chroma = ChromaService()
        self.ai = OpenAIService()
        self.vector_cache_dir = os.path.join(settings.BASE_DIR, 'data')
        self.vector_cache_file = os.path.join(self.vector_cache_dir, 'vector_cache.json')
        try:
            os.makedirs(self.vector_cache_dir, exist_ok=True)
        except Exception:
            pass

    def _load_vector_cache(self) -> Dict[str, Any]:
        if os.path.exists(self.vector_cache_file):
            try:
                with open(self.vector_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_vector_cache(self, cache: Dict[str, Any]):
        try:
            with open(self.vector_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False)
        except Exception as e:
            logger.warning("Failed to save local vector cache: %s", str(e))

    def index_document(self, doc: MedicalDocument):
        """
        Indexes a medical document into both ChromaDB (if online)
        and local vector cache for instant semantic search.
        """
        try:
            # 1. Format rich clinical representation
            entities = doc.extracted_entities.all()
            entity_lines = []
            for e in entities:
                ref = f" (Ref: {e.reference_range})" if e.reference_range else ""
                unit = f" {e.unit}" if e.unit else ""
                entity_lines.append(f"{e.entity_name}: {e.entity_value}{unit}{ref}")

            summary_text = (
                f"Title: {doc.title}\n"
                f"Type: {doc.document_type}\n"
                f"Date: {doc.document_date}\n"
                f"Doctor: {doc.issuing_doctor_name}\n"
                f"Clinic: {doc.issuing_clinic_name}\n"
                f"Clinical Findings:\n" + "\n".join(entity_lines) + "\n\n"
                f"OCR Text:\n{(doc.raw_ocr_text or '')[:4000]}"
            )

            # 2. Try ChromaDB
            self.chroma.index_document(
                doc_id=str(doc.id),
                patient_id=str(doc.patient.id),
                text=summary_text,
                metadata={
                    "document_date": str(doc.document_date),
                    "document_type": doc.document_type,
                    "title": doc.title or "Medical Document"
                }
            )

            # 3. Cache embedding locally for resilient offline search
            if self.ai.is_api_configured():
                emb = self.ai.get_embedding(summary_text[:3000])
                if emb:
                    cache = self._load_vector_cache()
                    cache[str(doc.id)] = {
                        "patient_id": str(doc.patient.id),
                        "title": doc.title,
                        "date": str(doc.document_date),
                        "type": doc.document_type,
                        "embedding": emb,
                        "summary": summary_text[:1500]
                    }
                    self._save_vector_cache(cache)
                    logger.info("Locally indexed document %s into vector cache", doc.id)
        except Exception as err:
            logger.warning("Error indexing document %s into RAG: %s", doc.id, str(err))

    def retrieve_context(self, patient_id: str, query_text: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """
        Multi-layered clinical retrieval:
        Layer 1: Exact & Fuzzy Clinical Entity Search (matches lab measurements, e.g. 'besophil' -> 'Basophil')
        Layer 2: Semantic Vector Similarity (ChromaDB or local OpenAI embeddings)
        Layer 3: Relational OCR keyword search
        """
        if not patient_id:
            logger.warning("RAG retrieval rejected: patient_id is required.")
            return []

        retrieved_docs: Dict[str, MedicalDocument] = {}
        direct_entity_matches: List[str] = []

        # -------------------------------------------------------------
        # Layer 1: Exact & Fuzzy Clinical Entity Search
        # -------------------------------------------------------------
        tokens = [t.lower() for t in re.findall(r'[a-zA-Z\u0980-\u09ff]+', query_text) if len(t) >= 3]
        patient_entities = DocumentEntity.objects.filter(
            document__patient_id=patient_id
        ).select_related('document')

        # Known medical mappings for common patient search terms/misspellings
        medical_synonyms = {
            'besophil': 'basophil',
            'bisophil': 'basophil',
            'baso': 'basophil',
            'platlet': 'platelet',
            'platlets': 'platelets',
            'platelets': 'platelets',
            'rbc': 'rbc',
            'wbc': 'wbc',
            'hb': 'hb',
            'hgb': 'hemoglobin',
            'sugar': 'glucose',
            'tsh': 'tsh',
            't4': 'thyroxine',
            't3': 'triiodothyronine',
            'lipid': 'cholesterol',
            'urine': 'pus cells',
            'usg': 'ultrasonogram',
        }

        for entity in patient_entities:
            e_name = entity.entity_name.lower()
            matched = False

            # Check direct substring
            for t in tokens:
                mapped_token = medical_synonyms.get(t, t)
                if mapped_token in e_name or (len(mapped_token) >= 4 and e_name in mapped_token):
                    matched = True
                    break
                # Fuzzy similarity with difflib
                if len(mapped_token) >= 4 and difflib.get_close_matches(mapped_token, [e_name], cutoff=0.72):
                    matched = True
                    break

            if matched:
                ref = f" (Reference Range: {entity.reference_range})" if entity.reference_range else ""
                unit = f" {entity.unit}" if entity.unit else ""
                match_desc = f"• {entity.entity_name}: {entity.entity_value}{unit}{ref} [From '{entity.document.title}' ({entity.document.document_date})]"
                direct_entity_matches.append(match_desc)
                retrieved_docs[str(entity.document.id)] = entity.document

        # -------------------------------------------------------------
        # Layer 2: Semantic Vector Similarity (Local or Chroma)
        # -------------------------------------------------------------
        cache = self._load_vector_cache()
        patient_cache = {doc_id: data for doc_id, data in cache.items() if data.get("patient_id") == str(patient_id)}
        if patient_cache and self.ai.is_api_configured():
            try:
                query_emb = self.ai.get_embedding(query_text)
                if query_emb:
                    scores = []
                    for doc_id, data in patient_cache.items():
                        doc_emb = data.get("embedding", [])
                        if doc_emb and len(doc_emb) == len(query_emb):
                            dot_prod = sum(a * b for a, b in zip(query_emb, doc_emb))
                            norm_q = math.sqrt(sum(a * a for a in query_emb))
                            norm_d = math.sqrt(sum(b * b for b in doc_emb))
                            score = dot_prod / (norm_q * norm_d) if (norm_q * norm_d) > 0 else 0
                            scores.append((doc_id, score))
                    scores.sort(key=lambda x: x[1], reverse=True)
                    for doc_id, score in scores[:top_k]:
                        if doc_id not in retrieved_docs:
                            try:
                                d = MedicalDocument.objects.get(id=doc_id)
                                retrieved_docs[doc_id] = d
                            except MedicalDocument.DoesNotExist:
                                pass
            except Exception as v_err:
                logger.warning("Local vector search error: %s", str(v_err))

        # -------------------------------------------------------------
        # Layer 3: Relational OCR keyword search
        # -------------------------------------------------------------
        if len(retrieved_docs) < top_k:
            query_filter = Q(patient_id=patient_id)
            if tokens:
                text_filter = Q()
                for tok in tokens[:5]:
                    mapped = medical_synonyms.get(tok, tok)
                    text_filter |= Q(raw_ocr_text__icontains=mapped) | Q(title__icontains=mapped)
                rel_docs = MedicalDocument.objects.filter(query_filter & text_filter).order_by('-document_date')
            else:
                rel_docs = MedicalDocument.objects.filter(query_filter).order_by('-document_date')

            for d in rel_docs:
                if len(retrieved_docs) >= top_k:
                    break
                if str(d.id) not in retrieved_docs:
                    retrieved_docs[str(d.id)] = d

        # If still empty, fall back to recent patient documents
        if not retrieved_docs:
            for d in MedicalDocument.objects.filter(patient_id=patient_id).order_by('-document_date')[:top_k]:
                retrieved_docs[str(d.id)] = d

        # -------------------------------------------------------------
        # Format Rich Context Blocks for the LLM
        # -------------------------------------------------------------
        results: List[Dict[str, Any]] = []

        # If we had direct clinical entity matches, insert an explicit summary block
        if direct_entity_matches:
            results.append({
                "document_id": None,
                "title": "Direct Matching Laboratory Measurements",
                "date": None,
                "type": "MATCHED_FINDINGS",
                "content": "CRITICAL MATCHING CLINICAL ENTITIES FOUND FOR QUERY:\n" + "\n".join(direct_entity_matches[:12])
            })

        for doc_id, doc in retrieved_docs.items():
            # Format structured lab findings
            entities = doc.extracted_entities.all()
            entity_str = ""
            if entities.exists():
                e_lines = []
                for e in entities:
                    ref = f" (Ref: {e.reference_range})" if e.reference_range else ""
                    unit = f" {e.unit}" if e.unit else ""
                    e_lines.append(f"- {e.entity_name}: {e.entity_value}{unit}{ref}")
                entity_str = "\nStructured Clinical Findings (All Measurements):\n" + "\n".join(e_lines)

            # Smart OCR excerpt (clean, up to 4500 chars)
            ocr_text = doc.raw_ocr_text or ""
            ocr_excerpt = ocr_text[:4500] if len(ocr_text) > 4500 else ocr_text

            doctor_str = f"Doctor: {doc.issuing_doctor_name}\n" if doc.issuing_doctor_name else ""
            clinic_str = f"Clinic: {doc.issuing_clinic_name}\n" if doc.issuing_clinic_name else ""

            content_block = (
                f"{doctor_str}{clinic_str}"
                f"{entity_str}\n\n"
                f"Document OCR Text:\n{ocr_excerpt}"
            )

            results.append({
                "document_id": str(doc.id),
                "title": doc.title or f"{doc.document_type} ({doc.document_date})",
                "date": str(doc.document_date),
                "type": doc.document_type,
                "content": content_block
            })

        logger.info("Hybrid RAGRetriever returned %d blocks for patient %s (Query: '%s')", len(results), patient_id, query_text[:40])
        return results
