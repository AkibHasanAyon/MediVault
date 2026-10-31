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
        Multi-page aware: processes multi-page documents concurrently per page
        to prevent entity omission, reference truncation, and token window exhaustion.
        Falls back to deterministic rule-based extraction in offline development.
        """
        if self.is_api_configured():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)

                # Check if multi-page structure is detected
                page_splits = re.split(r'--- PAGE \d+ ---', raw_ocr_text)
                pages_to_process = []
                for p_idx, p_text in enumerate(page_splits):
                    cleaned = p_text.strip()
                    if len(cleaned) > 50:
                        pages_to_process.append((cleaned, len(pages_to_process) + 1))

                if len(pages_to_process) > 1:
                    logger.info("Multi-page document detected (%d pages). Processing concurrently...", len(pages_to_process))
                    from concurrent.futures import ThreadPoolExecutor

                    def _extract_page(args):
                        p_content, p_num = args
                        resp = client.chat.completions.create(
                            model=self.model,
                            response_format={"type": "json_object"},
                            temperature=0.0,
                            max_tokens=3000,
                            messages=[
                                {"role": "system", "content": ENTITY_EXTRACTION_SYSTEM_PROMPT},
                                {"role": "user", "content": f"Document Page {p_num} OCR Text:\n\n{p_content}"}
                            ]
                        )
                        page_json = json.loads(resp.choices[0].message.content)
                        for item in page_json.get("lab_tests", []):
                            item["source_page"] = p_num
                        for med in page_json.get("medications", []):
                            med["source_page"] = p_num
                        return page_json

                    with ThreadPoolExecutor(max_workers=min(5, len(pages_to_process))) as executor:
                        page_results = list(executor.map(_extract_page, pages_to_process))

                    merged = self._merge_page_extractions(page_results)
                    self._validate_and_audit_extractions(raw_ocr_text, merged)
                    logger.info("Successfully extracted %d entities across %d pages",
                                len(merged.get('lab_tests', [])), len(pages_to_process))
                    return merged

                # Single page document
                response = client.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=4000,
                    messages=[
                        {"role": "system", "content": ENTITY_EXTRACTION_SYSTEM_PROMPT},
                        {"role": "user", "content": f"Extract all clinical entities from this OCR text:\n\n{raw_ocr_text}"}
                    ]
                )
                parsed = json.loads(response.choices[0].message.content)
                self._validate_and_audit_extractions(raw_ocr_text, parsed)
                logger.info("OpenAI GPT-4o-mini successfully parsed clinical entities: %d lab tests, %d meds",
                            len(parsed.get('lab_tests', [])), len(parsed.get('medications', [])))
                return parsed

            except Exception as e:
                logger.error("Failed to call OpenAI API for entity extraction: %s", str(e), exc_info=True)
                # Fall through to deterministic regex fallback so Celery task does not crash

        # Offline / Dev Fallback Parser
        logger.warning("Using rule-based offline entity extractor (OpenAI key not active).")
        return self._rule_based_fallback_parser(raw_ocr_text)

    def _merge_page_extractions(self, page_results: list[dict]) -> dict:
        """Merges structured clinical extractions from multiple document pages."""
        merged = {
            "document_type": "LAB_REPORT",
            "document_date": None,
            "title": None,
            "document_summary": "",
            "doctor_name": None,
            "clinic_name": None,
            "diagnoses": [],
            "medications": [],
            "lab_tests": [],
            "follow_up_advice": None,
        }

        # Hierarchy for document_type: RADIOLOGY or DISCHARGE or LAB_REPORT > PRESCRIPTION > OTHER
        doc_types = [p.get("document_type") for p in page_results if p.get("document_type")]
        if any(dt == "RADIOLOGY" for dt in doc_types):
            merged["document_type"] = "RADIOLOGY"
        elif any(dt == "LAB_REPORT" for dt in doc_types):
            merged["document_type"] = "LAB_REPORT"
        elif any(dt == "DISCHARGE" for dt in doc_types):
            merged["document_type"] = "DISCHARGE"
        elif any(dt == "PRESCRIPTION" for dt in doc_types):
            merged["document_type"] = "PRESCRIPTION"
        elif doc_types:
            merged["document_type"] = doc_types[0]

        for p in page_results:
            if not merged["doctor_name"] and p.get("doctor_name"):
                merged["doctor_name"] = p["doctor_name"]
            if not merged["clinic_name"] and p.get("clinic_name"):
                merged["clinic_name"] = p["clinic_name"]
            if not merged["document_date"] and p.get("document_date"):
                merged["document_date"] = p["document_date"]
            if not merged["follow_up_advice"] and p.get("follow_up_advice"):
                merged["follow_up_advice"] = p["follow_up_advice"]

            for d in p.get("diagnoses", []):
                if d and d not in merged["diagnoses"]:
                    merged["diagnoses"].append(d)

            for m in p.get("medications", []):
                merged["medications"].append(m)

            for lt in p.get("lab_tests", []):
                merged["lab_tests"].append(lt)

        # Smart title generation
        clinic = merged["clinic_name"]
        if merged["document_type"] == "RADIOLOGY":
            merged["title"] = f"Radiology / Ultrasound Report{f' - {clinic}' if clinic else ''}"
        elif merged["document_type"] == "LAB_REPORT":
            has_ultrasound = any("ultrasound" in str(lt.get("test_name", "")).lower() for lt in merged["lab_tests"])
            if has_ultrasound:
                merged["title"] = f"Diagnostic Lab & Ultrasound Report{f' - {clinic}' if clinic else ''}"
            else:
                merged["title"] = f"Diagnostic Lab Report{f' - {clinic}' if clinic else ''}"
        elif merged["document_type"] == "PRESCRIPTION":
            doctor = merged["doctor_name"]
            merged["title"] = f"Doctor Prescription{f' - {doctor}' if doctor else ''}"
        elif merged["document_type"] == "DISCHARGE":
            merged["title"] = f"Hospital Discharge Summary{f' - {clinic}' if clinic else ''}"
        else:
            merged["title"] = f"Medical Document{f' - {clinic}' if clinic else ''}"

        merged["document_summary"] = (
            f"Extracted {len(merged['lab_tests'])} laboratory & clinical findings, "
            f"{len(merged['medications'])} medications, and {len(merged['diagnoses'])} diagnoses."
        )
        return merged

    def _validate_and_audit_extractions(self, raw_text: str, result: dict) -> None:
        """
        Validation audit comparing extracted entities against source OCR text.
        Flags missing or unextracted clinical items and logs metrics.
        """
        extracted_tests = [t.get("test_name", "").lower() for t in result.get("lab_tests", [])]
        text_lower = raw_text.lower()

        core_biomarkers = [
            ("rbc", "RBC"),
            ("platelet", "Platelet Count"),
            ("mcv", "MCV"),
            ("glucose", "Glucose"),
            ("creatinine", "Creatinine"),
            ("cholesterol", "Cholesterol"),
            ("hdl", "HDL"),
            ("t4", "Total Thyroxine (T4)"),
            ("tsh", "TSH"),
            ("vitamin d", "Vitamin D"),
            ("pus", "Pus Cells"),
            ("epithelial", "Epithelial Cells"),
            ("ultrasound", "Ultrasound findings"),
        ]

        verified_count = 0
        audited_count = 0
        missing_findings = []

        for term, label in core_biomarkers:
            if term in text_lower:
                audited_count += 1
                if any(term in et for et in extracted_tests):
                    verified_count += 1
                else:
                    missing_findings.append(label)

        if missing_findings:
            logger.warning("Clinical Audit: Potential missed biomarkers in OCR text: %s", ", ".join(missing_findings))
        else:
            logger.info("Clinical Audit: All %d detectable core biomarkers successfully extracted.", verified_count)

        result["audit_metadata"] = {
            "audited_key_biomarkers": audited_count,
            "verified_key_biomarkers": verified_count,
            "missing_key_biomarkers": missing_findings,
            "total_lab_tests": len(result.get("lab_tests", [])),
            "total_medications": len(result.get("medications", [])),
            "total_diagnoses": len(result.get("diagnoses", [])),
            "status": "AUDIT_PASSED" if not missing_findings else "AUDIT_WARNING"
        }

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

        # Hemoglobin & CBC parameters fallback
        hb_match = re.search(r'(?:Hb|Hemoglobin)\s+([0-9]+\.?[0-9]*)\s*(gm/dl|g/dl)?', text, re.I)
        if hb_match:
            lab_tests.append({
                "test_name": "Hemoglobin (Hb)",
                "observed_value": hb_match.group(1),
                "unit": hb_match.group(2) or "gm/dl",
                "reference_range": "11.5 - 16.0",
                "is_abnormal": False
            })

        rbc_match = re.search(r'RBC\s+([0-9]+\.?[0-9]*)\s*(Million/Cmm)?', text, re.I)
        if rbc_match:
            lab_tests.append({
                "test_name": "RBC Count",
                "observed_value": rbc_match.group(1),
                "unit": rbc_match.group(2) or "Million/Cmm",
                "reference_range": "4.0 - 6.5",
                "is_abnormal": False
            })

        plt_match = re.search(r'Platelets?\s+([0-9,]+)\s*(/Cmm)?', text, re.I)
        if plt_match:
            lab_tests.append({
                "test_name": "Platelet Count",
                "observed_value": plt_match.group(1),
                "unit": plt_match.group(2) or "/Cmm",
                "reference_range": "150,000 - 450,000",
                "is_abnormal": False
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

