import os
import json
import logging
import re
from django.conf import settings
from .prompts import ENTITY_EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger('medivault.ai')

class OpenAIService:
    """
    OpenAI Client wrapper for GPT-4o-mini structured entity extraction
    and text-embedding-3-small vector embeddings.
    """

    def __init__(self):
        self.api_key = getattr(settings, 'OPENAI_API_KEY', '') or os.environ.get('OPENAI_API_KEY', '')
        self.model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
        self.embedding_model = getattr(settings, 'OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')

    def is_api_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith('sk-proj-your-openai'))

    def extract_clinical_entities(self, raw_ocr_text: str) -> dict:
        """
        Parses OCR raw text using GPT-4o-mini into structured JSON.
        Falls back to regex rule-based extraction in offline development.
        """
        if self.is_api_configured():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)

                response = client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    temperature=0.1,  # Low temperature for deterministic clinical extraction
                    messages=[
                        {"role": "system", "content": ENTITY_EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Extract clinical entities from this OCR text:\n\n{raw_ocr_text}"}
                    ]
                )
                parsed = json.loads(response.choices[0].message.content)
                logger.info("OpenAI GPT-4o-mini successfully parsed clinical entities")
                return parsed

            except Exception as e:
                logger.error("Failed to call OpenAI API for entity extraction: %s", str(e))
                # Fall through to deterministic regex fallback so Celery task does not crash

        # Offline / Dev Fallback Parser
        logger.warning("Using rule-based offline entity extractor (OpenAI key not active).")
        return self._rule_based_fallback_parser(raw_ocr_text)

    def get_embedding(self, text: str) -> list[float]:
        """Generates 1536-dimensional vector embedding for semantic search."""
        if self.is_api_configured():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)
                response = client.embeddings.create(
                    model=self.embedding_model,
                    input=text[:4000]  # Respect token window limits
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error("Failed to generate OpenAI embedding: %s", str(e))

        # 1536-dimensional normalized dummy vector for local development testing
        return [0.001] * 1536

    def _rule_based_fallback_parser(self, text: str) -> dict:
        """Deterministic regex parsing for local development when offline."""
        medications = []
        lab_tests = []
        diagnoses = []

        # Find medications e.g. "Tab. Nexum 20mg - 1+0+1"
        med_matches = re.findall(
            r'(?:Tab\.|Cap\.|Syr\.)\s+([A-Za-z0-9]+)\s+([0-9]+mg|[0-9]+ml)?\s*[-–]?\s*([0-9]\+[0-9]\+[0-9])?',
            text,
            re.IGNORECASE
        )
        for match in med_matches:
            brand = match[0]
            strength = match[1] or "Unspecified"
            pattern = match[2] or "1+0+1"
            medications.append({
                "brand_name": brand,
                "generic_name": None,
                "dosage_form": "Tablet",
                "strength": strength,
                "dosage_pattern": pattern,
                "timing_relation": "After Food",
                "duration_days": 30,
                "instructions": ""
            })

        # Find labs e.g. "Fasting Blood Glucose: 6.4 mmol/L"
        if "Glucose" in text:
            val_match = re.search(r'([0-9]+\.?[0-9]*)\s*mmol/L', text)
            if val_match:
                lab_tests.append({
                    "test_name": "Fasting Blood Glucose",
                    "observed_value": val_match.group(1),
                    "unit": "mmol/L",
                    "reference_range": "4.0 - 6.0",
                    "is_abnormal": float(val_match.group(1)) > 6.0
                })

        if "Diabetes" in text:
            diagnoses.append("Type 2 Diabetes Mellitus")

        # Classify document type
        doc_type = "OTHER"
        smart_title = "Health Document"
        if "discharge" in text.lower() or "admission" in text.lower():
            doc_type = "DISCHARGE"
            smart_title = "Discharge Summary"
        elif lab_tests or "test" in text.lower() or "investigation" in text.lower() or "cbc" in text.lower():
            doc_type = "LAB_REPORT"
            smart_title = "Diagnostic Lab Report"
        elif medications or "rx" in text.lower() or "℞" in text or "tab." in text.lower():
            doc_type = "PRESCRIPTION"
            smart_title = "Doctor Prescription"

        # Try to find date in text
        date_match = re.search(r'\b(20[2-3][0-9]-[0-1][0-9]-[0-3][0-9])\b', text)
        doc_date = date_match.group(1) if date_match else None

        # Try to find clinic name in text
        clinic_name = None
        clinic_match = re.search(
            r'([A-Za-z0-9 \t\.\-&]{3,40}(?:Diagnostic|Clinic|Hospital|Medical Center|Medical Centre|Lab|Laboratories)[A-Za-z0-9 \t\.\-]*)',
            text,
            re.IGNORECASE
        )
        if clinic_match:
            clinic_name = clinic_match.group(1).strip()

        # Try to find doctor name in text (prioritizing Referred By / Ref. By / Prescribed By)
        doctor_name = None
        ref_match = re.search(
            r'(?:Referred\s*By|Ref\.?\s*By|Ordered\s*By|Prescribed\s*By)\s*[:\-]?(?:[ \t]*[\r\n]+[ \t]*:?)?[ \t]*([^\r\n]+)',
            text,
            re.IGNORECASE
        )
        if ref_match:
            candidate = ref_match.group(1).strip()
            # Stop before adjacent metadata columns like Age, Sex, Date, Bed, etc.
            candidate = re.split(
                r'(?:\b(?:Age|Sex|Date|Pt|Patient|Bed|Cabin|Reg|Ref|Lab|Bill|Phone)\b[:\-])',
                candidate,
                flags=re.IGNORECASE
            )[0].strip()
            candidate = re.sub(r'[\s,\-]+$', '', candidate).strip()
            if len(candidate) > 2 and not candidate.lower().startswith('none'):
                doctor_name = candidate

        if not doctor_name:
            doc_match = re.search(r'((?:Dr\.|Prof\.|Professor)\s+[A-Za-z\s\.\-]{3,35})', text)
            if doc_match:
                doctor_name = doc_match.group(1).strip()

        return {
            "document_type": doc_type,
            "document_date": doc_date,
            "title": f"{smart_title}{f' - {clinic_name}' if clinic_name else ''}",
            "document_summary": f"Analyzed {smart_title}",
            "doctor_name": doctor_name,
            "clinic_name": clinic_name,
            "diagnoses": diagnoses,
            "medications": medications,
            "lab_tests": lab_tests,
            "follow_up_advice": None
        }

