# MediVault — Third-Party Integration & Services Specification

> **Vision Engine:** Google Cloud Vision API (`DOCUMENT_TEXT_DETECTION`)  
> **LLM & Embeddings:** OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`)  
> **Vector Database:** ChromaDB Client (HTTP Interface)  
> **Real-Time Layer:** Django Channels with Redis Channel Layer  
> **Task Processing:** Celery 5.x with Redis Broker  
> **SMS Gateway:** Bangladesh Bulk SMS Gateway (HTTP REST Adapter)  
> **PDF Engine:** WeasyPrint / ReportLab

---

## 1. Google Cloud Vision API Integration

Google Cloud Vision provides high-accuracy OCR for typed and handwritten prescriptions and lab reports, including support for mixed English and Bengali script.

### 1.1 Complete OCR Service (`apps/ai_services/ocr_service.py`)

```python
import io
import os
import logging
from google.cloud import vision
from PIL import Image, ImageEnhance, ImageFilter

logger = logging.getLogger(__name__)

class OCRResult:
    def __init__(self, raw_text: str, confidence: float, detected_languages: list):
        self.raw_text = raw_text
        self.confidence = confidence
        self.detected_languages = detected_languages

class OCRService:
    def __init__(self):
        # Assumes GOOGLE_APPLICATION_CREDENTIALS environment variable is set
        self.client = vision.ImageAnnotatorClient()

    def preprocess_image(self, image_path: str) -> bytes:
        """Enhances contrast, grayscale, and sharpness for faint thermal prints and low-light mobile scans."""
        with Image.open(image_path) as img:
            # Grayscale conversion
            img = img.convert('L')
            # Boost contrast
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.8)
            # Unsharp mask filter
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=95)
            return output.getvalue()

    def extract_text(self, image_path: str) -> OCRResult:
        try:
            image_bytes = self.preprocess_image(image_path)
            image = vision.Image(content=image_bytes)

            # Language hints optimize for Bengali medical documents with English drug names
            image_context = vision.ImageContext(language_hints=['en', 'bn'])
            response = self.client.document_text_detection(image=image, image_context=image_context)

            if response.error.message:
                logger.error(f"GCP Vision error: {response.error.message}")
                raise RuntimeError(response.error.message)

            annotation = response.full_text_annotation
            if not annotation:
                return OCRResult(raw_text="", confidence=0.0, detected_languages=[])

            raw_text = annotation.text.strip()
            confidence = annotation.pages[0].confidence if annotation.pages else 0.0
            
            languages = []
            if annotation.pages and annotation.pages[0].property:
                languages = [
                    lang.language_code 
                    for lang in annotation.pages[0].property.detected_languages
                ]

            return OCRResult(raw_text=raw_text, confidence=confidence, detected_languages=languages)

        except Exception as e:
            logger.exception("Failed to execute OCR via Google Cloud Vision")
            raise
```

---

## 2. OpenAI API Integration

OpenAI powers entity extraction, RAG embeddings, conversational Q&A, and drug interaction analysis using `gpt-4o-mini`.

### 2.1 Complete OpenAI Service (`apps/ai_services/openai_service.py`)

```python
import json
import logging
from openai import OpenAI
from django.conf import settings

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.chat_model = getattr(settings, 'OPENAI_MODEL', 'gpt-4o-mini')
        self.embedding_model = getattr(settings, 'OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')

    def get_embedding(self, text: str) -> list[float]:
        """Generates a 1536-dimensional vector for ChromaDB semantic indexing."""
        clean_text = text.replace("\n", " ").strip()
        response = self.client.embeddings.create(
            input=[clean_text],
            model=self.embedding_model
        )
        return response.data[0].embedding

    def extract_clinical_entities(self, ocr_text: str) -> dict:
        """Parses raw prescription/lab OCR text into structured clinical JSON."""
        system_prompt = (
            "You are MediVault Clinical Extraction AI. Extract medications, diagnoses, "
            "and lab results from the following OCR text. Output strictly a JSON object "
            "with keys: doctor, clinic_name, encounter_date, diagnoses, medications, lab_investigations."
        )

        response = self.client.chat.completions.create(
            model=self.chat_model,
            response_format={"type": "json_object"},
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"OCR Text:\n{ocr_text}"}
            ]
        )
        return json.loads(response.choices[0].message.content)

    def answer_rag_question(self, question: str, context_chunks: list[str], language: str = 'bn') -> str:
        """Answers patient questions grounded strictly in retrieved medical document chunks."""
        context_str = "\n\n---\n\n".join(context_chunks)
        lang_instruction = "Answer in natural, empathetic Bengali." if language == 'bn' else "Answer in clear English."

        system_prompt = (
            f"You are MediVault Personal Health Assistant. {lang_instruction} "
            "Rely strictly on the provided context from the patient's records. "
            "Never hallucinate data or provide direct medical diagnosis. "
            "Always state which doctor/date the information comes from."
        )

        user_content = f"Context from records:\n{context_str}\n\nPatient Question: {question}"

        response = self.client.chat.completions.create(
            model=self.chat_model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        )
        return response.choices[0].message.content

    def check_drug_interactions(self, active_meds: list, new_meds: list) -> dict:
        """Checks potential adverse drug-drug interactions."""
        system_prompt = (
            "You are a clinical pharmacology interaction checker. Compare active medications "
            "with newly prescribed medications. Output strictly a JSON object with: "
            "has_interactions (boolean), highest_severity ('NONE'|'MINOR'|'MODERATE'|'SEVERE_CONTRAINDICATED'), "
            "and alerts (array of {drugs_involved, severity, mechanism, clinical_management})."
        )

        payload = {
            "active_medications": active_meds,
            "new_medications": new_meds
        }

        response = self.client.chat.completions.create(
            model=self.chat_model,
            response_format={"type": "json_object"},
            temperature=0.0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload)}
            ]
        )
        return json.loads(response.choices[0].message.content)
```

---

## 3. ChromaDB Vector Database Integration

ChromaDB stores 1536-dimensional vector embeddings generated by `text-embedding-3-small`.

### 3.1 Chroma Service Class (`apps/ai_services/chroma_service.py`)

```python
import chromadb
from django.conf import settings
from .openai_service import OpenAIService

class ChromaService:
    def __init__(self):
        self.client = chromadb.HttpClient(
            host=getattr(settings, 'CHROMA_HOST', 'localhost'),
            port=int(getattr(settings, 'CHROMA_PORT', 8000))
        )
        self.collection = self.client.get_or_create_collection(
            name=getattr(settings, 'CHROMA_COLLECTION', 'medivault_patient_documents'),
            metadata={"hnsw:space": "cosine"}
        )
        self.ai = OpenAIService()

    def index_document(self, doc_id: str, patient_id: str, text: str, metadata: dict) -> str:
        """Embeds text and adds it to the ChromaDB vector store with patient isolation."""
        # Chunk text up to 2000 chars for embedding
        chunk = text[:2000]
        embedding = self.ai.get_embedding(chunk)
        
        full_metadata = {
            "patient_id": str(patient_id),
            "doc_id": str(doc_id),
            **metadata
        }

        self.collection.upsert(
            ids=[str(doc_id)],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[full_metadata]
        )
        return str(doc_id)

    def search_patient_documents(self, patient_id: str, query: str, n_results: int = 4) -> list[str]:
        """Performs vector search strictly filtered by patient_id."""
        query_embedding = self.ai.get_embedding(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where={"patient_id": str(patient_id)}
        )
        if results and results.get('documents') and len(results['documents']) > 0:
            return results['documents'][0]
        return []

    def delete_document(self, doc_id: str):
        """Removes a document from the vector index upon document deletion."""
        self.collection.delete(ids=[str(doc_id)])
```

---

## 4. Real-Time WebSockets (Django Channels)

### 4.1 Channel Routing (`config/routing.py`)
```python
from django.urls import re_path
from apps.appointments.consumers import ClinicQueueConsumer
from apps.notifications.consumers import UserNotificationConsumer

websocket_urlpatterns = [
    re_path(r'^ws/queue/(?P<clinic_id>[0-9a-f-]+)/$', ClinicQueueConsumer.as_asgi()),
    re_path(r'^ws/notifications/(?P<user_id>[0-9a-f-]+)/$', UserNotificationConsumer.as_asgi()),
]
```

### 4.2 ASGI Application Router (`config/asgi.py`)
```python
import os
import django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

import config.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            config.routing.websocket_urlpatterns
        )
    ),
})
```

---

## 5. Celery Asynchronous & Scheduled Task Engine

### 5.1 Celery App Setup (`config/celery.py`)
```python
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('medivault')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
```

### 5.2 Scheduled Tasks (Celery Beat Schedule in `config/settings/base.py`)
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Run on 1st of every month at midnight UTC
    'generate-monthly-health-reports': {
        'task': 'apps.reports.tasks.generate_all_monthly_reports_task',
        'schedule': crontab(day_of_month='1', hour='0', minute='0'),
    },
    # Check every 15 minutes for pending medication doses
    'dispatch-medication-reminders': {
        'task': 'apps.medications.tasks.dispatch_medication_reminders_task',
        'schedule': crontab(minute='*/15'),
    },
    # Check daily at 9:00 AM for follow-up escalations
    'check-follow-up-escalations': {
        'task': 'apps.appointments.tasks.check_follow_up_escalations_task',
        'schedule': crontab(hour='9', minute='0'),
    },
    # Clean up expired QR sharing tokens every hour
    'cleanup-expired-shares': {
        'task': 'apps.sharing.tasks.cleanup_expired_shares_task',
        'schedule': crontab(minute='0', hour='*'),
    },
}
```

---

## 6. Messaging & Notifications Integration (SMTP Email & SMS Gateway)

To avoid high per-message SMS costs during development, testing, and prototype phases, MediVault uses an **adaptable messaging layer (`MessagingService`)**:
- **Phase 1 & Prototype (Default):** Delivers OTP verification codes, Chamber Queue token alerts, Danger vital alerts, and medication reminders via **SMTP Email** using your configured SMTP credentials (e.g., Gmail, SendGrid, Mailgun, Amazon SES, or custom mail server).
- **Production Launch:** Seamlessly toggle to **Bangladesh SMS Gateway** (BulkSMSBD / SSL Wireless) by switching `MESSAGING_BACKEND=sms` in `.env` without modifying business logic.

```mermaid
graph TD
    Trigger["Event: OTP / Queue Serial / Danger Alert / Reminder"] --> Dispatcher["MessagingService.dispatch()"]
    Dispatcher --> Check{"MESSAGING_BACKEND in settings"}
    Check -->|'email' (Dev / Prototype)| Email["EmailService (SMTP)"]
    Check -->|'sms' (Production)| SMS["SMSService (HTTP REST API)"]
    Email --> RecipientEmail["Patient / Doctor Inbox"]
    SMS --> RecipientPhone["Patient Mobile Handset"]
```

### 6.1 SMTP Email Service Implementation (`apps/notifications/email_service.py`)

```python
import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_notification_email(
        recipient_email: str,
        subject: str,
        template_name: str,
        context: dict
    ) -> bool:
        """
        Sends responsive HTML notification emails using Django's SMTP backend.
        Supports OTP codes, chamber token updates, and danger vital alerts.
        """
        try:
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'MediVault <no-reply@medivault.app>')
            
            # Render HTML and plain-text fallback
            html_content = render_to_string(f'emails/{template_name}.html', context)
            text_content = strip_tags(html_content)

            msg = EmailMultiAlternatives(
                subject=f"[MediVault] {subject}",
                body=text_content,
                from_email=from_email,
                to=[recipient_email]
            )
            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)

            logger.info(f"Email successfully sent to {recipient_email} with subject: {subject}")
            return True

        except Exception as e:
            logger.exception(f"Failed to dispatch email to {recipient_email}: {str(e)}")
            return False

    @classmethod
    def send_otp_email(cls, recipient_email: str, otp_code: str, user_name: str = "User") -> bool:
        return cls.send_notification_email(
            recipient_email=recipient_email,
            subject="Your Verification Code (OTP)",
            template_name="otp_verification",
            context={"user_name": user_name, "otp_code": otp_code, "valid_minutes": 5}
        )

    @classmethod
    def send_queue_token_email(
        cls,
        recipient_email: str,
        patient_name: str,
        token_number: int,
        doctor_name: str,
        est_wait_min: int
    ) -> bool:
        return cls.send_notification_email(
            recipient_email=recipient_email,
            subject=f"Chamber Token Serial: #{token_number}",
            template_name="queue_token_alert",
            context={
                "patient_name": patient_name,
                "token_number": token_number,
                "doctor_name": doctor_name,
                "est_wait_min": est_wait_min
            }
        )

    @classmethod
    def send_danger_alert_email(
        cls,
        recipient_email: str,
        patient_name: str,
        alert_type: str,
        trigger_value: str,
        instructions: str
    ) -> bool:
        return cls.send_notification_email(
            recipient_email=recipient_email,
            subject=f"URGENT: Critical Health Alert ({alert_type})",
            template_name="danger_vital_alert",
            context={
                "patient_name": patient_name,
                "alert_type": alert_type,
                "trigger_value": trigger_value,
                "instructions": instructions
            }
        )
```

### 6.2 Unified Messaging Dispatcher (`apps/notifications/messaging_service.py`)

```python
import logging
from django.conf import settings
from .email_service import EmailService
from .sms_service import SMSService

logger = logging.getLogger(__name__)

class MessagingService:
    """
    Unified entry point for all notifications.
    Dynamically routes to SMTP Email or SMS Gateway based on MESSAGING_BACKEND setting.
    """

    @staticmethod
    def send_otp(recipient_phone: str, recipient_email: str, otp_code: str, user_name: str = "User") -> bool:
        backend = getattr(settings, 'MESSAGING_BACKEND', 'email').lower()

        if backend == 'email' and recipient_email:
            logger.info(f"Routing OTP to SMTP Email ({recipient_email}) for cost saving in dev/prototype.")
            return EmailService.send_otp_email(recipient_email, otp_code, user_name)
        elif backend == 'sms' and recipient_phone:
            logger.info(f"Routing OTP to SMS Gateway ({recipient_phone}) in production.")
            message = f"Your MediVault verification code is: {otp_code}. Valid for 5 minutes."
            return SMSService.send_sms(recipient_phone, message)
        else:
            # Fallback to email if phone SMS is unavailable
            if recipient_email:
                return EmailService.send_otp_email(recipient_email, otp_code, user_name)
            logger.warning(f"No valid dispatch channel for user {user_name}.")
            return False

    @staticmethod
    def send_queue_notification(
        recipient_phone: str,
        recipient_email: str,
        patient_name: str,
        token_number: int,
        doctor_name: str,
        est_wait_min: int
    ) -> bool:
        backend = getattr(settings, 'MESSAGING_BACKEND', 'email').lower()

        if backend == 'email' and recipient_email:
            return EmailService.send_queue_token_email(
                recipient_email, patient_name, token_number, doctor_name, est_wait_min
            )
        else:
            message = f"MediVault: Token #{token_number} with {doctor_name}. Est. wait: {est_wait_min}m."
            return SMSService.send_sms(recipient_phone, message)

    @staticmethod
    def send_danger_alert(
        recipient_phone: str,
        recipient_email: str,
        patient_name: str,
        alert_type: str,
        trigger_value: str,
        instructions: str
    ) -> bool:
        backend = getattr(settings, 'MESSAGING_BACKEND', 'email').lower()

        # In production, dispatch both email AND SMS for critical danger alerts!
        success_email = True
        if recipient_email:
            success_email = EmailService.send_danger_alert_email(
                recipient_email, patient_name, alert_type, trigger_value, instructions
            )

        if backend == 'sms' and recipient_phone:
            message = f"MediVault CRITICAL: {alert_type} ({trigger_value}). {instructions}"
            SMSService.send_sms(recipient_phone, message)

        return success_email
```

### 6.3 Production SMS Service Class (`apps/notifications/sms_service.py`)

```python
import logging
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

class SMSService:
    @staticmethod
    def send_sms(phone_number: str, message: str) -> bool:
        """Dispatches an SMS to a Bangladeshi phone number (+8801XXXXXXXXX)."""
        api_key = getattr(settings, 'SMS_API_KEY', '')
        sender_id = getattr(settings, 'SMS_SENDER_ID', 'MediVault')

        if not api_key:
            logger.warning(f"[MOCK SMS - API KEY MISSING] To: {phone_number} | Message: {message}")
            return True

        url = "https://bulksmsbd.net/api/smsapi"
        payload = {
            "api_key": api_key,
            "type": "text",
            "number": phone_number,
            "senderid": sender_id,
            "message": message
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                res = client.post(url, data=payload)
                if res.status_code == 200:
                    logger.info(f"SMS successfully dispatched to {phone_number}")
                    return True
                else:
                    logger.error(f"SMS Gateway returned non-200: {res.text}")
                    return False
        except Exception as e:
            logger.exception(f"Failed to dispatch SMS to {phone_number}")
            return False
```

---

## 7. PDF Report Generation Integration (WeasyPrint)

Used to render pixel-perfect, printable PDF documents for:
1. **Monthly Health Reports** (vitals graphs + AI summary).
2. **Digital Prescriptions** (official doctor letterhead + Rx details).

### 7.1 Report PDF Service (`apps/reports/pdf_service.py`)
```python
import io
from django.template.loader import render_to_string
from weasyprint import HTML

class PDFReportService:
    @staticmethod
    def generate_monthly_report_pdf(report_context: dict) -> bytes:
        html_string = render_to_string('reports/monthly_health_report.html', report_context)
        html = HTML(string=html_string)
        pdf_bytes = html.write_pdf()
        return pdf_bytes

    @staticmethod
    def generate_prescription_pdf(prescription_context: dict) -> bytes:
        html_string = render_to_string('prescriptions/prescription_letterhead.html', prescription_context)
        html = HTML(string=html_string)
        pdf_bytes = html.write_pdf()
        return pdf_bytes
```

