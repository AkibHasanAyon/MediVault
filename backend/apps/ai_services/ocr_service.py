import os
import io
import base64
import logging
from pathlib import Path
import requests
from PIL import Image, ImageEnhance
from django.conf import settings

logger = logging.getLogger('medivault.ocr')

class OCRService:
    """
    Google Cloud Vision OCR Client with image & multi-page PDF support.
    Extracts printed and handwritten Bengali/English medical text.
    Handles:
      1. Image files (.jpg, .png, .webp, .tiff) with contrast preprocessing
      2. PDF files (.pdf) using pypdfium2 page rendering + Vision OCR per page
    """

    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_API_KEY', '') or os.environ.get('GOOGLE_API_KEY', '')
        self.credentials_path = getattr(settings, 'GOOGLE_APPLICATION_CREDENTIALS', '') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')

    def preprocess_image(self, file_path: str) -> str:
        """Enhances contrast and converts color profile before passing to OCR."""
        try:
            path = Path(file_path)
            ext = path.suffix.lower()
            if ext in ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.heic', '.heif']:
                if ext in ['.heic', '.heif']:
                    import pillow_heif
                    pillow_heif.register_heif_opener()

                with Image.open(file_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    # Contrast boost for faded thermal or carbon-copy paper
                    enhancer = ImageEnhance.Contrast(img)
                    enhanced_img = enhancer.enhance(1.2)
                    preprocessed_path = str(path.parent / f"prep_{path.stem}.jpg")
                    enhanced_img.save(preprocessed_path, format='JPEG', quality=95)
                    return preprocessed_path
        except Exception as e:
            logger.warning("Image preprocessing failed, proceeding with original: %s", str(e))
        return file_path

    def _ocr_image_bytes(self, image_bytes: bytes) -> str:
        """Sends raw image bytes (JPEG/PNG) to Google Cloud Vision Document Text Detection."""
        if not self.api_key:
            logger.warning("GOOGLE_API_KEY is not configured.")
            return ""

        try:
            content_b64 = base64.b64encode(image_bytes).decode('utf-8')
            url = f"https://vision.googleapis.com/v1/images:annotate?key={self.api_key}"
            payload = {
                "requests": [
                    {
                        "image": {"content": content_b64},
                        "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
                        "imageContext": {
                            "languageHints": ["bn", "en"]
                        }
                    }
                ]
            }
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                data = res.json()
                responses = data.get("responses", [])
                if responses and "error" in responses[0]:
                    err_msg = responses[0]["error"].get("message", "Unknown error")
                    logger.error("GCP Vision REST error: %s", err_msg)
                    return ""

                if responses:
                    full_text = responses[0].get("fullTextAnnotation", {})
                    text = full_text.get("text", "")
                    if not text and "textAnnotations" in responses[0] and responses[0]["textAnnotations"]:
                        text = responses[0]["textAnnotations"][0].get("description", "")
                    return text.strip()
            else:
                logger.warning("GCP Vision returned HTTP %s: %s", res.status_code, res.text[:200])

        except Exception as e:
            logger.error("Failed to call GCP Vision for image bytes: %s", str(e))

        return ""

    def _extract_from_pdf(self, file_path: str) -> dict:
        """
        Extracts text from multi-page PDFs:
        1. Checks for digital text embedded in PDF.
        2. Renders pages to images using pypdfium2 and runs Vision OCR.
        """
        combined_text = []

        # 1. Check for embedded digital text via pypdf
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            digital_pages = []
            for i, page in enumerate(reader.pages):
                pt = page.extract_text() or ""
                if len(pt.strip()) > 50:
                    digital_pages.append(f"--- PAGE {i+1} ---\n{pt.strip()}")
            if digital_pages:
                logger.info("Extracted embedded digital text from %d PDF pages", len(digital_pages))
                combined_text.extend(digital_pages)
        except Exception as e:
            logger.debug("Digital text extraction failed or was empty: %s", str(e))

        # 2. Render pages to images using pypdfium2 if digital text is minimal or for scanned PDFs
        if not combined_text:
            try:
                import pypdfium2 as pdfium
                pdf = pdfium.PdfDocument(file_path)
                num_pages = min(len(pdf), 8)  # Process up to 8 pages to respect resource limits
                logger.info("Rendering %d scanned PDF page(s) with pypdfium2 for OCR", num_pages)

                for page_idx in range(num_pages):
                    pil_image = pdf[page_idx].render(scale=1.5).to_pil()
                    buf = io.BytesIO()
                    pil_image.save(buf, format='JPEG', quality=90)
                    page_ocr = self._ocr_image_bytes(buf.getvalue())
                    if page_ocr:
                        combined_text.append(f"--- PAGE {page_idx+1} ---\n{page_ocr}")

                pdf.close()
            except Exception as e:
                logger.error("pypdfium2 PDF page rendering failed: %s", str(e))

        final_text = "\n\n".join(combined_text).strip()
        if final_text:
            logger.info("Successfully extracted %d characters from PDF %s", len(final_text), file_path)
            return {
                "raw_text": final_text,
                "provider": "GOOGLE_CLOUD_VISION_PDF",
                "success": True
            }

        logger.warning("No text could be extracted from PDF %s", file_path)
        return {
            "raw_text": "",
            "provider": "NONE",
            "success": False
        }

    def extract_text(self, file_path: str) -> dict:
        """
        Unified extraction method handling both images and PDFs.
        Returns {"raw_text": str, "provider": str, "success": bool}.
        """
        if not os.path.exists(file_path):
            logger.error("File does not exist at path: %s", file_path)
            return {"raw_text": "", "provider": "NONE", "success": False}

        path = Path(file_path)
        suffix = path.suffix.lower()

        # Handle PDF documents
        if suffix == '.pdf':
            return self._extract_from_pdf(file_path)

        # Handle Image files
        processed_path = self.preprocess_image(file_path)
        try:
            with open(processed_path, 'rb') as f:
                img_bytes = f.read()
            text = self._ocr_image_bytes(img_bytes)
            if text:
                return {
                    "raw_text": text,
                    "provider": "GOOGLE_CLOUD_VISION_REST",
                    "success": True
                }
        except Exception as e:
            logger.error("Image OCR failed for %s: %s", file_path, str(e))

        return {
            "raw_text": "",
            "provider": "NONE",
            "success": False
        }

    def extract_text_from_image(self, file_path: str) -> dict:
        """Backward-compatible alias for existing tasks."""
        return self.extract_text(file_path)
