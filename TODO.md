# MediVault — Phase-wise Implementation Tracker & Master TODO

> **Document Status:** Active Living Tracker (100% Aligned with `docs/Implementation.md`)  
> **Last Synchronized:** October 2026  
> **Target Region:** Bangladesh Healthcare Ecosystem (`Asia/Dhaka`, BDT)  
> **Architecture:** Django 5.x ASGI/WSGI + DRF + Celery + Redis + Channels + Postgres 16 + React 18 Prototype

---

## 📊 Master Progress Dashboard

| Metric | Status |
|---|---|
| **Overall Project Completion** | **0%** (`0 / 9 Phases Complete` · `0 / 64 Tasks Done`) |
| **Current Active Phase** | **Phase 1: Foundation & Infrastructure (Weeks 1–2)** |
| **Messaging Channel Mode** | `MESSAGING_BACKEND=email` (Zero-cost SMTP dev mode) |
| **Next Actionable Task** | `T1.1: Monorepo Directory Scaffolding` |

### 🗺️ 9-Phase Roadmap Alignment

This tracker is synchronized 1-to-1 with [docs/Implementation.md](file:///c:/Users/User/Desktop/Medivault%20resources/MediVault/docs/Implementation.md):

| Phase | Guide Section | Focus & Core Deliverables | Timeline | Tasks | Status |
|:---:|---|---|:---:|:---:|:---:|
| **1** | [Section 2](#phase-1-foundation-infrastructure--authentication-weeks-12) | Docker, Django 5 Scaffolding, Custom User, JWT, Swagger, SMTP Dispatcher | Weeks 1–2 | 8 | `PENDING` |
| **2** | [Section 3](#phase-2-core-data-models--database-migrations-weeks-23) | 11 Domain Apps, Base Models, Foreign Keys, Physiological Limits, Initial Migrations | Weeks 2–3 | 8 | `PENDING` |
| **3** | [Section 4](#phase-3-document-processing--ocr-pipeline-weeks-34) | Upload API, Celery Workers, GCP Vision OCR, GPT-4o-mini Extraction, ChromaDB Index | Weeks 3–4 | 7 | `PENDING` |
| **4** | [Section 5](#phase-4-health-monitoring--danger-alert-system-weeks-45) | Vitals CRUD, Danger Alerts (Hypo/Hyper/Crisis OR), Meds Schedule & Adherence | Weeks 4–5 | 8 | `PENDING` |
| **5** | [Section 6](#phase-5-ai-clinical-intelligence-rag--monthly-reports-weeks-57) | ChromaDB RAG, Bilingual Bangla/English "Ask AI", Pre-Intake, 10-Sec Brief, WeasyPrint PDF | Weeks 5–7 | 7 | `PENDING` |
| **6** | [Section 7](#phase-6-scoped-qr-consultation--digital-prescriptions-weeks-78) | 30-Min Ephemeral HMAC QR, Doctor Scanner, Digital Rx Canvas, Drug Interactions | Weeks 7–8 | 8 | `PENDING` |
| **7** | [Section 8](#phase-7-real-time-chamber-queue-websockets-weeks-89) | Django Channels WebSocket, Live Queue Consumer, Assistant & Doctor Desk, Multi-Channel Serial Alerts | Weeks 8–9 | 6 | `PENDING` |
| **8** | [Section 9](#phase-8-reactjs-prototype-frontend-weeks-912) | React 18 + Vite + Tailwind, 3 Role Portals (Patient, Doctor, Assistant), WebSockets | Weeks 9–12 | 6 | `PENDING` |
| **9** | [Section 10 & 11](#phase-9-testing-security-hardening--quality-gates-weeks-1314) | Pytest Suite ($\ge 80\%$ Coverage), Celery/Channels Tests, Security Audit, Quality Gates | Weeks 13–14 | 7 | `PENDING` |

---

## 🛠️ Instructions for Developers & AI Pair Programmers
1. **Always consult this file before starting work** to identify the next sequential task.
2. When starting a task, mark it as `[-] In Progress` and note the timestamp.
3. Upon task completion and successful test execution, toggle the checkbox to `[x]`, update task status to `COMPLETED`, and increment the dashboard progress counters.
4. **Strict Sequencing:** MediVault's clinical data dependencies require strict sequential layering (e.g., custom user before domain profiles; domain models before OCR extraction).

---

## Phase 1: Foundation, Infrastructure & Authentication (Weeks 1–2)

**Implementation Guide Reference:** [docs/Implementation.md § 2](file:///c:/Users/User/Desktop/Medivault%20resources/MediVault/docs/Implementation.md#2-phase-1-foundation--infrastructure-weeks-12)

- [ ] **Task 1.1: Monorepo Directory Scaffolding & Virtual Environment**
  - Create directory layout: `/backend`, `/frontend`, `/docs`.
  - Set up Python virtual environment (`python -m venv venv`) and initialize Git repo.
  - *Target Files:* `backend/`, `frontend/`, `.gitignore`
  - *Verification:* `python --version` returns 3.12+; virtualenv activates cleanly.

- [ ] **Task 1.2: Environment & Secrets Configuration**
  - Copy `.env.example` to `.env`.
  - Configure `SECRET_KEY`, `DEBUG=True`, `DATABASE_URL`, and local database credentials.
  - Set `MESSAGING_BACKEND=email` for zero-cost SMTP verification.
  - *Target Files:* `.env`, `backend/config/settings/base.py`
  - *Verification:* `python -c "import environ; print('Env loaded successfully')"`

- [ ] **Task 1.3: Docker Compose Services Validation**
  - Bring up PostgreSQL 16, Redis 7, and ChromaDB vector store.
  - *Target Files:* `docker-compose.yml`
  - *Verification:* `docker compose up -d db redis chromadb` runs healthy; `docker ps` shows all 3 services running.

- [ ] **Task 1.4: Django 5 Project Initialization & Modular Settings**
  - Initialize Django project: `django-admin startproject config .`
  - Split settings into `config/settings/base.py`, `development.py`, and `production.py`.
  - Configure installed apps: `rest_framework`, `rest_framework_simplejwt`, `corsheaders`, `drf_spectacular`, `channels`.
  - *Target Files:* `backend/config/settings/*`, `backend/manage.py`
  - *Verification:* `python manage.py check` executes without warnings.

- [ ] **Task 1.5: Celery Task Broker Setup**
  - Configure Celery app with Redis broker (`redis://localhost:6379/1`).
  - Configure Celery beat scheduler for periodic background health jobs.
  - *Target Files:* `backend/config/celery.py`, `backend/config/__init__.py`
  - *Verification:* `celery -A config worker --loglevel=info` connects to Redis cleanly.

- [ ] **Task 1.6: Custom User Model Implementation**
  - Create `apps/accounts/models.py` with `User(AbstractBaseUser, PermissionsMixin)`.
  - Fields: `id (UUID)`, `phone_number` (unique, E.164 index), `email` (unique, indexed), `full_name`, `role` (`PATIENT`, `DOCTOR`, `ASSISTANT`, `ADMIN`), `is_phone_verified`, `preferred_language` (`bn`/`en`).
  - Configure `AUTH_USER_MODEL = 'accounts.User'`.
  - *Target Files:* `backend/apps/accounts/models.py`, `backend/apps/accounts/managers.py`
  - *Verification:* `python manage.py makemigrations accounts` applies initial migration cleanly.

- [ ] **Task 1.7: Unified Messaging Service (SMTP Email & SMS Dispatcher)**
  - Implement `EmailService` utilizing Django's SMTP backend (`django.core.mail`).
  - Implement `SMSGatewayService` abstraction for live mobile carriers.
  - Create `MessagingService` dispatcher reading `MESSAGING_BACKEND` (`email` vs `sms`).
  - *Target Files:* `backend/apps/notifications/services.py`, `backend/apps/notifications/email_service.py`
  - *Verification:* Unit test dispatches test email to local mailbox/console when `MESSAGING_BACKEND=email`.

- [ ] **Task 1.8: JWT Authentication, OTP Verification & Swagger UI (`drf-spectacular`)**
  - Implement `POST /api/v1/auth/register/` (dispatches 6-digit OTP via email/SMS).
  - Implement `POST /api/v1/auth/verify-phone/` (validates OTP, returns JWT access & refresh tokens).
  - Configure OpenAPI 3.1 generator with JWT Bearer security scheme.
  - Wire `/api/v1/schema/`, `/api/v1/docs/` (Swagger UI), and `/api/v1/redoc/`.
  - *Target Files:* `backend/apps/accounts/views.py`, `backend/config/urls.py`
  - *Verification:* Navigating to `http://localhost:8000/api/v1/docs/` renders interactive Swagger dashboard.

---

## Phase 2: Core Data Models & Database Migrations (Weeks 2–3)

**Implementation Guide Reference:** [docs/Implementation.md § 3](file:///c:/Users/User/Desktop/Medivault%20resources/MediVault/docs/Implementation.md#3-phase-2-core-data-models--migrations-weeks-23)

- [ ] **Task 2.1: Common Base Model & Soft Deletion**
  - Implement `TimeStampedUUIDModel` (`id UUID`, `created_at`, `updated_at`).
  - Implement soft deletion manager and queryset filters.
  - *Target Files:* `backend/apps/common/models.py`
  - *Verification:* Unit test confirms soft-deleted instances are excluded from standard `.objects.all()` queries.

- [ ] **Task 2.2: User Profiles (Patients, Doctors, Clinics, Assistants)**
  - `PatientProfile`: DOB/age, gender, blood group, allergies (text, default "None reported"), emergency contact.
  - `DoctorProfile`: BM&DC registration number, qualifications, specialties, bio, chamber address, is_verified.
  - `Clinic`: Name, address, phone, geolocation coordinates, license.
  - `ClinicAssistantProfile`: Clinic foreign key, desk identification, is_active.
  - *Target Files:* `backend/apps/patients/models.py`, `backend/apps/doctors/models.py`, `backend/apps/clinics/models.py`
  - *Verification:* Signals auto-create profile on User creation based on `user.role`.

- [ ] **Task 2.3: Family Member Profiles**
  - `FamilyMember`: Foreign key to `PatientProfile`, relation (`PARENT`, `SPOUSE`, `CHILD`, `OTHER`), name, DOB, blood group.
  - Enforce constraint: Maximum 8 family profiles per master account.
  - *Target Files:* `backend/apps/patients/models.py`
  - *Verification:* Attempting to save a 9th family member raises validation error.

- [ ] **Task 2.4: Daily Health Logs (Vitals)**
  - `BloodGlucoseLog`: `glucose_value_mmol`, meal context (`FASTING`, `POST_MEAL`, `BEDTIME`, `RANDOM`), timestamp, `is_danger`.
  - `BloodPressureLog`: `systolic_mmHg`, `diastolic_mmHg`, `pulse_bpm`, timestamp, `is_danger`.
  - `WeightLog`: `weight_kg`, calculated BMI.
  - `SymptomNote`: Note text, severity (`MILD`, `MODERATE`, `SEVERE`), onset time.
  - Add hard limits validation (e.g. Glucose 0.5–60 mmol/L, Systolic 40–300 mmHg).
  - *Target Files:* `backend/apps/health_logs/models.py`, `backend/apps/health_logs/validators.py`
  - *Verification:* Migrations apply; inserting out-of-bound vital values triggers `ValidationError`.

- [ ] **Task 2.5: Medical Documents & Extracted Entities**
  - `MedicalDocument`: Patient FK, family member FK (optional), file path, document type (`PRESCRIPTION`, `LAB_REPORT`, `DISCHARGE_SUMMARY`, `OTHER`), document date, status (`UPLOADED`, `PROCESSING_OCR`, `EXTRACTION_COMPLETE`, `FAILED`).
  - `DocumentEntity`: Document FK, entity category (`MEDICATION`, `LAB_TEST`, `DIAGNOSIS`), raw text, normalized name, numerical value, unit, reference range, confidence score.
  - *Target Files:* `backend/apps/documents/models.py`
  - *Verification:* Composite indexes on `[patient, document_date]` created in PostgreSQL.

- [ ] **Task 2.6: Prescriptions & Medication Reminders**
  - `Prescription`: Doctor FK, Patient FK, chamber name, clinical notes, diagnosis tags.
  - `PrescriptionMedication`: Brand name, generic name, strength, dosage form, schedule pattern (`1+0+1`), instructions, duration.
  - `Medication`: Active patient medication roster (verified vs unverified provenance flag).
  - `MedicationReminder`: Dose time, notification enabled flag.
  - `MedicationAdherence`: Action (`TAKEN`, `SKIPPED`, `SNOOZED`), scheduled time, recorded time, reason.
  - *Target Files:* `backend/apps/prescriptions/models.py`, `backend/apps/medications/models.py`
  - *Verification:* Schema correctly establishes FK relationship between prescriptions and patient reminders.

- [ ] **Task 2.7: Appointments & Chamber Queue Models**
  - `Appointment`: Patient FK, Doctor FK, Clinic FK, scheduled date, slot time, status (`SCHEDULED`, `COMPLETED`, `CANCELLED`, `NO_SHOW`).
  - `QueueEntry`: Clinic FK, Doctor FK, Appointment FK (optional), serial token (`A-001`), arrival timestamp, status (`WAITING`, `IN_CONSULTATION`, `DONE`, `SKIPPED`), estimated wait minutes.
  - *Target Files:* `backend/apps/appointments/models.py`
  - *Verification:* Unique constraint on `[clinic, doctor, scheduled_date, serial_number]` enforced.

- [ ] **Task 2.8: Scoped Sharing & Consultation Handshake**
  - `ConsultationShare`: Patient FK, Doctor FK (nullable until claimed), token hash (SHA-256), scope array (`permitted_document_ids`, `permitted_metric_types`), `is_active`, `expires_at` (strict 30-min default).
  - `ShareAuditLog`: Share FK, Doctor FK, IP address, user agent, accessed timestamp, action.
  - *Target Files:* `backend/apps/sharing/models.py`
  - *Verification:* `expires_at` defaults to `now() + timedelta(minutes=30)`.

---

## Phase 3: Document Processing & OCR Pipeline (Weeks 3–4)

**Implementation Guide Reference:** [docs/Implementation.md § 4](file:///c:/Users/User/Desktop/Medivault%20resources/MediVault/docs/Implementation.md#4-phase-3-document-processing-pipeline-weeks-34)

- [ ] **Task 3.1: Document Upload ViewSet & Format Validation**
  - Implement `POST /api/v1/documents/upload/` supporting JPEG, PNG, WebP, and multi-page PDF.
  - Inspect magic bytes (limit 10 MB per file); reject malicious file headers.
  - Store files under randomized UUID paths (`/media/documents/%Y/%m/<uuid>.<ext>`).
  - *Target Files:* `backend/apps/documents/validators.py`, `backend/apps/documents/views.py`
  - *Verification:* Uploading a 5 MB prescription image returns `202 Accepted` with `document_id`.

- [ ] **Task 3.2: Asynchronous Celery OCR Task Pipeline**
  - Build `process_document_ocr_task(document_id)`:
    - Preprocess image (contrast enhancement, auto-rotation via Pillow).
    - Dispatch to Google Cloud Vision API `document_text_detection`.
    - Persist raw text and word-level bounding polygon JSON.
  - Update document status to `PROCESSING_EXTRACTION`.
  - *Target Files:* `backend/apps/documents/tasks.py`, `backend/apps/documents/services/vision_service.py`
  - *Verification:* Upload sample prescription JPEG; verify raw text is extracted and saved to DB.

- [ ] **Task 3.3: Google Cloud Vision API Client**
  - Implement `OCRService` in `apps/ai_services/ocr_service.py`.
  - Handle rate limiting and retry with exponential backoff.
  - Support both Bengali and English handwriting detection.
  - *Target Files:* `backend/apps/ai_services/ocr_service.py`
  - *Verification:* Test OCR on Bangla diagnostic report; returns extracted Bangla and English strings.

- [ ] **Task 3.4: OpenAI GPT-4o-mini Clinical Entity Parser**
  - Construct strict JSON schema prompt instructing GPT-4o-mini to extract:
    - Medications (brand, generic, dosage, frequency, duration, instructions).
    - Lab tests (test name, observed numerical value, unit, reference range, abnormal flag).
    - Doctor name, clinic name, date of visit.
  - Enforce zero hallucination rule: null for unmentioned values.
  - *Target Files:* `backend/apps/ai_services/openai_service.py`, `backend/apps/ai_services/prompts.py`
  - *Verification:* Extract from sample text; verify output parses strictly into Pydantic schema.

- [ ] **Task 3.5: ChromaDB Semantic Vector Indexing**
  - Index OCR extracted text into ChromaDB collection `medivault_patient_documents`.
  - Generate embeddings using OpenAI `text-embedding-3-small`.
  - Attach metadata: `patient_id`, `document_id`, `document_type`, `date`.
  - *Target Files:* `backend/apps/ai_services/chroma_service.py`
  - *Verification:* Query vector index with "blood sugar test" returns relevant lab report chunks.

- [ ] **Task 3.6: Patient Extraction Review & Correction API**
  - `GET /api/v1/documents/{id}/`: Detail view returning side-by-side original image URL and unverified entities.
  - `PUT /api/v1/documents/{id}/review/`: Patient reviews and confirms/corrects values; marks `user_confirmed=True`.
  - *Target Files:* `backend/apps/documents/serializers.py`, `backend/apps/documents/views.py`
  - *Verification:* Modifying a dosage strength via review API updates entity provenance to `PATIENT_CONFIRMED`.

- [ ] **Task 3.7: Chronological Patient Timeline API**
  - `GET /api/v1/documents/timeline/`: Unified chronological feed of all documents, lab results, and clinic visits.
  - Filtering by `document_type`, date range, and `family_member_id`.
  - *Target Files:* `backend/apps/documents/views.py`
  - *Verification:* Filter by `PRESCRIPTION` returns sorted prescriptions with thumbnail URLs.

---

## Phase 4: Health Monitoring & Danger Alert System (Weeks 4–5)

**Implementation Guide Reference:** [docs/Implementation.md § 5](file:///c:/Users/User/Desktop/Medivault%20resources/MediVault/docs/Implementation.md#5-phase-4-health-monitoring--danger-alert-system-weeks-45)

- [ ] **Task 4.1: Blood Glucose Vitals API & Context Tagging**
  - `POST /api/v1/health-logs/blood-glucose/`: Log glucose in `mmol/L` (auto-convert if `mg/dL` passed).
  - Measurement contexts: `FASTING`, `POST_MEAL`, `BEDTIME`, `RANDOM`.
  - Hard limit validation: reject values `< 0.5` or `> 60.0 mmol/L`.
  - *Target Files:* `backend/apps/health_logs/serializers.py`, `backend/apps/health_logs/views.py`
  - *Verification:* Inputting `5.4 mmol/L` saves successfully; inputting `99 mmol/L` returns 400 Bad Request.

- [ ] **Task 4.2: Blood Pressure & Pulse Tracking**
  - `POST /api/v1/health-logs/blood-pressure/`: Record `systolic_mmHg`, `diastolic_mmHg`, and `pulse_bpm`.
  - Hard limit validation: reject systolic `< 40` or `> 300`, diastolic `< 30` or `> 200`.
  - Auto-categorize BP stage (Normal, Elevated, Stage 1, Stage 2, Crisis).
  - *Target Files:* `backend/apps/health_logs/models.py`, `backend/apps/health_logs/services.py`
  - *Verification:* Entering `120/80` categorizes as `NORMAL`; `160/100` categorizes as `STAGE_2`.

- [ ] **Task 4.3: Weight, BMI & Symptom Logging**
  - `POST /api/v1/health-logs/weight/`: Record weight in `kg`; compute BMI from patient height.
  - `POST /api/v1/health-logs/symptoms/`: Multi-tag symptom logger with severity scale.
  - *Target Files:* `backend/apps/health_logs/views.py`
  - *Verification:* Adding weight updates BMI metric card.

- [ ] **Task 4.4: Algorithmic Danger Alert Engine (Clinical Standards)**
  - Implement Django post-save signals on vitals models:
    - **Hypoglycemia Alert:** Glucose `< 3.9 mmol/L`
    - **Hyperglycemia Alert:** Glucose `> 16.0 mmol/L`
    - **Hypertensive Crisis Alert:** `Systolic > 180 OR Diastolic > 120 mmHg` (Standardized `OR` logic)
  - Create `DangerAlert` record with clinically approved immediate safety instructions.
  - *Target Files:* `backend/apps/health_logs/signals.py`, `backend/apps/health_logs/alert_engine.py`
  - *Verification:* Saving BP `185/85` triggers Hypertensive Crisis alert (even though diastolic < 120).

- [ ] **Task 4.5: Danger Alert WebSocket & Emergency Messaging Dispatch**
  - Publish alert immediately to Redis channel layer `user_{patient_id}_alerts`.
  - Queue `send_emergency_alert_task` to dispatch urgent notification via `MessagingService` (SMTP email in dev, SMS in prod).
  - Alert contains direct emergency contact (**999**) instructions.
  - *Target Files:* `backend/apps/health_logs/tasks.py`, `backend/apps/notifications/consumers.py`
  - *Verification:* Glucose 3.1 mmol/L generates WebSocket event in `< 200ms` and sends email notification.

- [ ] **Task 4.6: Active Medication Roster & Frequency Parser**
  - Parse prescription frequency patterns:
    - `1+0+1` $\rightarrow$ 08:00 AM, 08:00 PM
    - `1+1+1` $\rightarrow$ 08:00 AM, 02:00 PM, 08:00 PM
    - `0+0+1` $\rightarrow$ 09:00 PM
  - Generate `MedicationReminder` instances for patient review.
  - Allow patient to adjust alert times without changing prescription dosage.
  - *Target Files:* `backend/apps/medications/services/schedule_builder.py`
  - *Verification:* Pattern `1+0+1` generates two reminder slots at 08:00 and 20:00.

- [ ] **Task 4.7: Daily Medication Dose Center & Adherence Logging**
  - `GET /api/v1/medications/today/`: Returns today's doses sorted by time slot (Morning, Noon, Night).
  - Status indicators: `PENDING`, `TAKEN`, `SKIPPED`, `SNOOZED`.
  - Calculate adherence percentage: $\frac{\text{Doses Taken}}{\text{Scheduled Doses}} \times 100$.
  - Enforce medical rule: Never recommend double or catch-up doses after skipped meds.
  - *Target Files:* `backend/apps/medications/views.py`, `backend/apps/medications/services/adherence.py`
  - *Verification:* Marking dose TAKEN decrements remaining refill count by 1.

- [ ] **Task 4.8: Celery Beat 15-Minute Reminder Dispatcher**
  - Set up Celery Beat task `dispatch_scheduled_medication_reminders` running every 15 minutes.
  - Query reminders due in the current 15-minute window with `notification_enabled=True`.
  - Dispatch in-app push and email notification via `MessagingService`.
  - *Target Files:* `backend/apps/medications/tasks.py`
  - *Verification:* Triggering Celery task delivers notification for doses scheduled at matching time.

---

## Phase 5: AI Clinical Intelligence, RAG & Monthly Reports (Weeks 5–7)

**Implementation Guide Reference:** [docs/Implementation.md § 6](file:///c:/Users/User/Desktop/Medivault%20resources/MediVault/docs/Implementation.md#6-phase-5-ai-rag--monthly-reports-weeks-57)

- [ ] **Task 5.1: ChromaDB RAG Vector Retriever**
  - Implement RAG retrieval pipeline:
    - Receive user health query in Bangla or English.
    - Generate query embedding via OpenAI `text-embedding-3-small`.
    - Retrieve top 4 relevant document chunks scoped strictly to `patient_id`.
  - Reject queries attempting to search other patients' collections.
  - *Target Files:* `backend/apps/ai_services/rag_retriever.py`
  - *Verification:* RAG search for "fasting sugar" returns relevant prescription & lab test chunks.

- [ ] **Task 5.2: Grounded Q&A Chat Engine ("Ask AI")**
  - `POST /api/v1/ai/ask/`: Conversational RAG endpoint.
  - System prompt enforcing strict clinical safety rules:
    - Never diagnose diseases, change dosages, or suggest alternative drugs.
    - Ground all statements in cited documents with clickable source references.
    - If answer is not in patient documents, state clearly: *"আপনার আপলোডকৃত ডকুমেন্টে এই তথ্যটি পাওয়া যায়নি।"*
    - Answer in the same language as the question (Bangla or English).
  - *Target Files:* `backend/apps/ai_services/views.py`, `backend/apps/ai_services/prompts.py`
  - *Verification:* Asking "আমার কি ওষুধ খাওয়া উচিত?" triggers polite medical refusal and recommendation to see a doctor.

- [ ] **Task 5.3: Conversation History & Context Threads**
  - Store chat sessions in `AIConversation` and `AIMessage`.
  - Support multi-turn Q&A within 5-message context sliding window.
  - `GET /api/v1/ai/conversations/` and `GET /api/v1/ai/conversations/{id}/messages/`.
  - *Target Files:* `backend/apps/ai_services/models.py`, `backend/apps/ai_services/views.py`
  - *Verification:* Second question in chat context correctly references previous question's medication.

- [ ] **Task 5.4: Pre-Appointment 3-Question Intake Synthesis**
  - `POST /api/v1/appointments/{id}/pre-summary/`: Intake questionnaire:
    1. *What is your primary concern for this visit?*
    2. *What symptoms have you experienced recently?*
    3. *Have you noticed any medication side effects?*
  - Synthesize answers with 90-day vital averages into a 1-page structured doctor brief.
  - *Target Files:* `backend/apps/appointments/services/intake_synthesis.py`
  - *Verification:* Submitting intake triggers GPT-4o-mini synthesis returning SOAP-style brief.

- [ ] **Task 5.5: 10-Second Doctor Pre-Consultation Synthesis**
  - `GET /api/v1/doctor/patients/{id}/brief/`:
    - 90-day glucose & BP averages (SQL computed deterministically).
    - Danger alert incident count.
    - Active medications list.
    - AI-synthesized 3-bullet clinical summary with source document links.
  - Cached in Redis with 10-minute TTL for sub-second chamber page loads.
  - *Target Files:* `backend/apps/doctors/services/brief_service.py`
  - *Verification:* Endpoint executes in $< 100\text{ms}$ when cached in Redis.

- [ ] **Task 5.6: Vector HTML/CSS Monthly Health Report Template**
  - Design HTML/CSS template for vector PDF:
    - Monthly vital trend charts (SVG embedded).
    - Medication adherence percentage gauge.
    - Uploaded documents list and doctor visit logs.
    - AI monthly overview narrative.
  - *Target Files:* `backend/apps/reports/templates/monthly_report.html`
  - *Verification:* Template renders cleanly in browser with Bangla font styling (`Noto Sans Bengali`).

- [ ] **Task 5.7: WeasyPrint PDF Generation & Celery 1st-of-Month Dispatch**
  - Convert HTML to PDF via `weasyprint`.
  - Set up Celery Beat task `generate_monthly_health_reports` running on the 1st of each month at 00:00 UTC.
  - Generate reports for all active patients for the preceding calendar month.
  - Send email notification with PDF attachment / secure download link via `MessagingService`.
  - *Target Files:* `backend/apps/reports/tasks.py`, `backend/apps/reports/services/pdf_builder.py`
  - *Verification:* `weasyprint` outputs clean, multi-page vector PDF; Celery task logs successful generation.

---

## Phase 6: Scoped QR Consultation & Digital Prescriptions (Weeks 7–8)

**Implementation Guide Reference:** [docs/Implementation.md § 7](file:///c:/Users/User/Desktop/Medivault%20resources/MediVault/docs/Implementation.md#7-phase-6-qr-consultation--prescriptions-weeks-78)

- [ ] **Task 6.1: Ephemeral QR Token Generation (Patient)**
  - `POST /api/v1/sharing/qr/generate/`:
    - Patient selects permitted scope (`all_documents`, `last_30_days`, specific record IDs).
    - Generate HMAC-SHA256 signature using server secret + random nonce.
    - Store token in Redis with strict 1,800-second (30 min) TTL.
    - Return payload for vector QR rendering on mobile screen.
  - *Target Files:* `backend/apps/sharing/services/qr_service.py`, `backend/apps/sharing/views.py`
  - *Verification:* Token payload decrypts with valid signature and Redis key expires after 30 minutes.

- [ ] **Task 6.2: Doctor QR Scan & Handshake Authorization**
  - `POST /api/v1/doctor/consultation/scan-qr/`:
    - Authenticated doctor scans patient QR code.
    - Validates token against Redis; binds handshake to `doctor_id`.
    - Creates `ConsultationShare` session and writes `ShareAuditLog`.
    - Returns scoped patient medical history and 10-second brief.
  - *Target Files:* `backend/apps/sharing/views.py`, `backend/apps/sharing/services/audit_service.py`
  - *Verification:* Doctor scan unlocks patient timeline; audit log records doctor license, chamber IP, and timestamp.

- [ ] **Task 6.3: Patient In-Session Revocation Endpoint**
  - `DELETE /api/v1/sharing/{id}/revoke/`:
    - Patient taps `[Revoke Doctor Access]` on phone.
    - Instantly purges token from Redis and marks `is_active=False` in DB.
    - Subsequent doctor requests return `403 Forbidden`.
  - *Target Files:* `backend/apps/sharing/views.py`
  - *Verification:* Calling revoke immediately blocks doctor endpoint access within $< 100\text{ms}$.

- [ ] **Task 6.4: Digital Prescription Writer Canvas API**
  - `POST /api/v1/doctor/prescriptions/`:
    - Chamber header (doctor name, degrees, BM&DC reg, clinic branch).
    - Patient details (name, age, vitals snapshot).
    - Clinical notes, complaints, diagnosis tags.
    - Array of prescribed medicines (brand, generic, dosage, instructions, duration).
    - Next follow-up recommendation (e.g. "Review after 3 months").
  - *Target Files:* `backend/apps/prescriptions/serializers.py`, `backend/apps/prescriptions/views.py`
  - *Verification:* Creating prescription saves record and returns generated prescription ID.

- [ ] **Task 6.5: Real-Time Drug Interaction Checking Engine**
  - `POST /api/v1/doctor/prescriptions/check-interactions/`:
    - Cross-reference newly prescribed medicines against patient's existing active medications.
    - Query known interaction rules (e.g. Metformin + contrast agents, ACE inhibitors + Potassium).
    - Return severity level (`CONTRAINDICATED`, `SEVERE`, `MODERATE`, `INFO`) and clinical explanation.
    - Require doctor explicit clinical override note if prescribing contraindicated pair.
  - *Target Files:* `backend/apps/prescriptions/services/interaction_service.py`
  - *Verification:* Checking Metformin + Ciprofloxacin returns warning of enhanced hypoglycemic effect.

- [ ] **Task 6.6: Closed-Loop Digital Prescription $\rightarrow$ Patient Reminders**
  - On prescription finalization, execute post-save handler:
    - Populate patient's active `Medication` roster.
    - Auto-create draft `MedicationReminder` entries for patient review.
    - Create `FollowUpReminder` matching recommended return date.
  - Push prescription notification to patient app via WebSocket.
  - *Target Files:* `backend/apps/prescriptions/signals.py`
  - *Verification:* Finalizing prescription immediately makes medications visible in patient's app.

- [ ] **Task 6.7: Clinic-Branded Prescription PDF Generator**
  - `GET /api/v1/doctor/prescriptions/{id}/pdf/`:
    - Render standard Bangladesh prescription layout (Rx symbol, doctor chamber header, medicines table, advice, follow-up).
    - Generate vector PDF via `weasyprint` / `reportlab`.
  - *Target Files:* `backend/apps/prescriptions/services/prescription_pdf.py`
  - *Verification:* PDF matches standard clinic layout with QR verification watermark.

- [ ] **Task 6.8: Smart Follow-Up Memory & Escalated Reminders**
  - Parse follow-up advice (e.g. "Review after 3 months").
  - Create scheduled reminder milestones:
    - Milestone 1: **2.5 months** (Early appointment booking reminder)
    - Milestone 2: **1 week before** (Upcoming visit reminder)
    - Milestone 3: **Due date** (Checkup due today)
  - Celery Beat daily task checks and dispatches due reminders via `MessagingService`.
  - *Target Files:* `backend/apps/appointments/services/follow_up_engine.py`, `backend/apps/appointments/tasks.py`
  - *Verification:* Setting 3-month follow-up generates 3 escalating reminder rows with correct future trigger dates.

---

## Phase 7: Real-Time Chamber Queue WebSockets (Weeks 8–9)

**Implementation Guide Reference:** [docs/Implementation.md § 8](file:///c:/Users/User/Desktop/Medivault%20resources/MediVault/docs/Implementation.md#8-phase-7-real-time-chamber-queue-websockets-weeks-89)

- [ ] **Task 7.1: Django Channels ASGI Setup & Redis Channel Layer**
  - Configure `asgi.py` with `ProtocolTypeRouter` for HTTP and WebSocket traffic.
  - Configure `channels_redis.core.RedisChannelLayer`.
  - Implement JWT authentication middleware for WebSocket connections (`apps/common/channels_auth.py`).
  - *Target Files:* `backend/config/asgi.py`, `backend/config/routing.py`, `backend/apps/common/channels_auth.py`
  - *Verification:* WebSocket connection to `ws://localhost:8000/ws/` authenticates successfully with Bearer token.

- [ ] **Task 7.2: `ClinicQueueConsumer` WebSocket Consumer**
  - Create `ClinicQueueConsumer` listening on room group `queue_clinic_{clinic_id}`.
  - Broadcast queue events: `TOKEN_ISSUED`, `PATIENT_CALLED`, `CONSULTATION_STARTED`, `CONSULTATION_ENDED`, `PATIENT_SKIPPED`.
  - *Target Files:* `backend/apps/appointments/consumers.py`
  - *Verification:* Connecting two `wscat` clients to same clinic room verifies message broadcast in $< 50\text{ms}$.

- [ ] **Task 7.3: Clinic Assistant Queue Desk API**
  - `POST /api/v1/assistant/queue/assign-token/`:
    - Fast phone number lookup (prevents duplicate patient registration).
    - Issue sequential daily serial token (`A-001`, `A-002`).
    - Estimate wait time based on average consultation duration (e.g. 7 mins/patient).
  - `GET /api/v1/assistant/queue/today/`: Live roster table with status indicators.
  - *Target Files:* `backend/apps/appointments/views/assistant_views.py`
  - *Verification:* Assigning token generates sequential serial number and broadcasts WebSocket event.

- [ ] **Task 7.4: Doctor In-Chamber Live Queue Desk API**
  - `GET /api/v1/doctor/queue/live/`: Returns current patient in room, next 3 waiting patients, and completed count.
  - `PUT /api/v1/doctor/queue/{id}/call-in/`: Doctor clicks "Call In" $\rightarrow$ updates status, pushes live notification.
  - *Target Files:* `backend/apps/appointments/views/doctor_views.py`
  - *Verification:* Calling in a patient updates assistant board and triggers patient notification simultaneously.

- [ ] **Task 7.5: Automated Serial Call-In Notifications via MessagingService**
  - When patient is 2 serials away from consultation, dispatch automated alert:
    - *"আপনার সিরিয়াল নং A-012। আপনার পূর্বে আর ২ জন রোগী আছেন। অনুগ্রহ করে চেম্বারের সামনে প্রস্তুত থাকুন।"*
  - Routed through `MessagingService` (SMTP email in dev, SMS in prod).
  - *Target Files:* `backend/apps/appointments/services/queue_notifier.py`
  - *Verification:* Calling token A-010 triggers automated notification dispatch to patient holding token A-012.

- [ ] **Task 7.6: End-of-Day Clinic Chamber Analytics API**
  - `GET /api/v1/assistant/queue/daily-summary/`:
    - Total patients registered vs seen.
    - Average consultation duration.
    - Average patient waiting time.
    - No-show and cancellation rate.
  - *Target Files:* `backend/apps/appointments/views/assistant_views.py`
  - *Verification:* Summary accurately aggregates daily queue entries.

---

## Phase 8: React.js Prototype Frontend (Weeks 9–12)

**Implementation Guide Reference:** [docs/Implementation.md § 9](file:///c:/Users/User/Desktop/Medivault%20resources/MediVault/docs/Implementation.md#9-phase-8-reactjs-prototype-frontend-weeks-912)

- [ ] **Task 8.1: React 18 + Vite + TypeScript Scaffolding & Design System**
  - Initialize React 18 + Vite + TypeScript in `/frontend`.
  - Install dependencies: `tailwindcss`, `lucide-react`, `recharts`, `axios`, `react-router-dom`, `@tanstack/react-query`, `qrcode.react`.
  - Configure MediVault color tokens (`#087E8B`, `#16324F`, `#2A9D8F`, `#E76F51`, `#F4A261`).
  - Configure typography: Noto Sans Bengali & Inter.
  - *Target Files:* `frontend/package.json`, `frontend/tailwind.config.js`, `frontend/src/index.css`
  - *Verification:* `npm run dev` starts Vite development server on `http://localhost:3000`.

- [ ] **Task 8.2: Role-Based Routing & Axios JWT Interceptor**
  - Implement Axios interceptor for JWT automatic access token attachment and refresh flow.
  - Build protected routes: `/patient/*`, `/doctor/*`, `/assistant/*`.
  - Implement sign-in, OTP verification, and role switcher UI.
  - *Target Files:* `frontend/src/api/client.ts`, `frontend/src/routes/AppRoutes.tsx`, `frontend/src/context/AuthContext.tsx`
  - *Verification:* Logging in as Doctor redirects to Doctor Chamber Desk; direct access to Patient routes is blocked.

- [ ] **Task 8.3: Patient Webapp Implementation**
  - Health Log cards (Glucose, BP, Weight) with Recharts 90-day time-series graphs.
  - Document Vault: Camera / file upload modal, timeline feed, side-by-side OCR extraction review.
  - Medication reminder cards with "Taken" / "Skip" toggles and adherence progress ring.
  - "Ask AI" conversational drawer with bilingual chat and citation pills.
  - Ephemeral QR Code modal for doctor sharing.
  - *Target Files:* `frontend/src/pages/patient/*`, `frontend/src/components/patient/*`
  - *Verification:* Uploading document renders in timeline; clicking Ask AI returns cited streaming answer.

- [ ] **Task 8.4: Doctor Chamber Desk Implementation**
  - Live Chamber Queue sidebar synchronized via WebSocket.
  - Ephemeral QR scanner component unlocking patient records.
  - 10-Second Pre-Consultation Brief panel (vitals averages, danger history, active meds).
  - Digital Prescription Writer canvas with medication typeahead and interaction warning alerts.
  - *Target Files:* `frontend/src/pages/doctor/*`, `frontend/src/components/doctor/*`
  - *Verification:* Scanning test QR opens patient brief; prescribing interacting drug triggers warning dialog.

- [ ] **Task 8.5: Clinic Assistant Desk Implementation**
  - Walk-in patient registration form (phone lookup, name, doctor selection).
  - Sequential token generator with live wait-time counter.
  - Live queue board table with 1-click status actions ("Call In", "Done", "Skip").
  - End-of-day summary metrics dashboard.
  - *Target Files:* `frontend/src/pages/assistant/*`, `frontend/src/components/assistant/*`
  - *Verification:* Adding walk-in patient immediately updates queue table and increments token count.

- [ ] **Task 8.6: Responsive UI & Localization (Noto Sans Bengali)**
  - Ensure mobile viewport responsiveness across all screens.
  - Implement language switcher (English $\leftrightarrow$ Bangla).
  - Maintain clinical units in English for medical safety.
  - *Target Files:* `frontend/src/i18n/*`, `frontend/src/components/common/Header.tsx`
  - *Verification:* Switching to Bangla updates UI text while keeping blood glucose unit as `mmol/L`.

---

## Phase 9: Testing, Security Hardening & Quality Gates (Weeks 13–14)

**Implementation Guide Reference:** [docs/Implementation.md § 10 & 11](file:///c:/Users/User/Desktop/Medivault%20resources/MediVault/docs/Implementation.md#10-phase-9-testing-security-hardening--production-audit-weeks-1314)

- [ ] **Task 9.1: Pytest Test Suite Configuration & Model Factories**
  - Configure `backend/pytest.ini` with Django settings.
  - Create test factories using `factory-boy` (`UserFactory`, `PatientProfileFactory`, `BloodGlucoseLogFactory`, etc.).
  - *Target Files:* `backend/pytest.ini`, `backend/tests/factories.py`
  - *Verification:* `pytest` runs and discovers test files.

- [ ] **Task 9.2: Authentication & RBAC Test Suite**
  - Auth tests: Registration, OTP verification via email, invalid codes, token refresh.
  - Security tests: Role boundary enforcement, unshared record access rejection (`403 Forbidden`).
  - *Target Files:* `backend/tests/test_auth.py`, `backend/tests/test_permissions.py`
  - *Verification:* Pytest passes all auth and permission test cases.

- [ ] **Task 9.3: Clinical Data & Vitals Test Suite**
  - Test danger alert triggers: Hypoglycemia (`< 3.9`), Hyperglycemia (`> 16.0`).
  - Test Hypertensive Crisis `OR` condition (`Systolic > 180 OR Diastolic > 120 mmHg`).
  - Test hard limits validation (rejection of typos).
  - *Target Files:* `backend/tests/test_vitals.py`, `backend/tests/test_alerts.py`
  - *Verification:* Saving BP `185/85` confirms crisis alert creation; invalid vitals reject with 400.

- [ ] **Task 9.4: Celery Eager Tasks & Django Channels WebSocket Tests**
  - Test Celery tasks in eager mode (`CELERY_TASK_ALWAYS_EAGER=True`).
  - Test `ClinicQueueConsumer` using `channels.testing.WebsocketCommunicator`.
  - *Target Files:* `backend/tests/test_tasks.py`, `backend/tests/test_channels.py`
  - *Verification:* Communicator verifies WebSocket broadcast on token status update.

- [ ] **Task 9.5: Production Security Hardening**
  - Validate production environment variables (`DEBUG=False`, explicit `ALLOWED_HOSTS`).
  - Enforce SSL/TLS, secure cookie flags (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`), and HSTS headers.
  - Configure endpoint rate limiting (throttles for auth, OCR, and AI queries).
  - *Target Files:* `backend/config/settings/production.py`
  - *Verification:* `python manage.py check --deploy` passes with 0 critical security warnings.

- [ ] **Task 9.6: Production Multi-Stage Docker Builds**
  - Build multi-stage production Docker containers for Django Daphne ASGI, Celery workers, and React frontend.
  - *Target Files:* `Dockerfile`, `docker-compose.prod.yml`
  - *Verification:* `docker compose -f docker-compose.prod.yml build` succeeds cleanly.

- [ ] **Task 9.7: Final Verification & Quality Gates Audit**
  - Verify all 6 quality gates defined in `docs/Implementation.md § 11`:
    1. `python manage.py check --deploy` (0 critical warnings)
    2. `python manage.py makemigrations --check` (0 unstaged changes)
    3. `pytest` ($\ge 80\%$ test coverage)
    4. `flake8` and `npm run lint` (0 errors)
    5. WebSocket communicator tests pass
    6. Celery tasks execute without unhandled exceptions
  - *Verification:* All 6 verification gates passed and signed off.

---

## 📝 Change Log & Task Tracking History

| Date & Time | Phase | Task ID | Action Taken | Engineer / Agent |
|---|:---:|:---:|---|---|
| 2026-10-29 19:40 | Setup | All | Re-synchronized TODO.md to 100% 1-to-1 match docs/Implementation.md (9 Phases) | Antigravity AI |
| *Upcoming* | 1 | T1.1 | Initialize backend & frontend directories | — |

---

> [!IMPORTANT]
> **Tracking Protocol:** When implementing tasks, open this file, replace `- [ ]` with `- [x]`, update the progress counter at the top, and log the completed task with timestamp in the Change Log above.
