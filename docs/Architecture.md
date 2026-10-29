# MediVault — System Architecture & Technical Specifications

> **Target Version:** 1.0.0  
> **Backend Framework:** Django 5.x with Django REST Framework (DRF) & Django Channels (ASGI)  
> **Frontend Stack:** React 18+ (Prototype), Flutter / React Native (Final Mobile)  
> **AI & Vision:** OpenAI API (GPT-4o-mini, text-embedding-3-small), Google Cloud Vision API  
> **Persistence & Caching:** PostgreSQL 16, ChromaDB (Vector Store), Redis 7 (Broker & Channels Layer)

---

## 1. High-Level Architecture Overview

MediVault is designed around a modular monolithic architecture with asynchronous event-driven pipelines for compute-heavy AI/OCR workloads and real-time bidirectional communication for clinical chamber operations.

```mermaid
graph TD
    subgraph Clients ["Client Layer"]
        C1["Patient Mobile App<br/>(Flutter / React Native)"]
        C2["Doctor Desktop Chamber<br/>(React Web / Tablet)"]
        C3["Assistant Queue Desk<br/>(React Web / Tablet)"]
    end

    subgraph Gateway ["Reverse Proxy & Ingress"]
        Nginx["Nginx Reverse Proxy<br/>SSL Termination / Static / Media"]
    end

    subgraph App_Server ["Application Server Layer (Django ASGI/WSGI)"]
        ASGI["Daphne / Uvicorn ASGI Server<br/>WebSocket Endpoints (/ws/*)"]
        WSGI["Gunicorn WSGI Server<br/>REST API Endpoints (/api/v1/*)"]
        DjangoCore["Django 5.x Core Engine<br/>Auth, RBAC, ORM, Signals, Business Logic"]
    end

    subgraph Background ["Async & Scheduled Tasks"]
        CeleryWorker["Celery Workers<br/>Async OCR, AI Extraction, PDF Generation"]
        CeleryBeat["Celery Beat Scheduler<br/>Monthly Reports, Medication Reminders"]
    end

    subgraph Data_Storage ["Data & State Persistence"]
        PG[("PostgreSQL 16<br/>Relational Core Data")]
        VDB[("ChromaDB<br/>Vector Store & Embeddings")]
        RedisCore[("Redis 7<br/>Cache & Celery Broker")]
        RedisChannel[("Redis 7<br/>Channels Layer")]
        MediaStore["Media Storage<br/>Encrypted Documents & Reports"]
    end

    subgraph External_Services ["External AI & Third-Party APIs"]
        GCV["Google Cloud Vision API<br/>Document Text Detection (OCR)"]
        OpenAI["OpenAI API<br/>GPT-4o-mini & Embeddings"]
        SMS["Bangladesh SMS Gateway<br/>OTP & Queue Token SMS"]
    end

    C1 & C2 & C3 -->|HTTPS / WSS| Nginx
    Nginx -->|HTTP REST| WSGI
    Nginx -->|WebSocket| ASGI
    WSGI & ASGI --> DjangoCore
    DjangoCore --> PG
    DjangoCore --> RedisCore
    ASGI --> RedisChannel

    DjangoCore -->|Dispatch Task| RedisCore
    RedisCore --> CeleryWorker
    CeleryBeat --> RedisCore
    CeleryWorker --> PG
    CeleryWorker --> VDB
    CeleryWorker --> MediaStore

    CeleryWorker -->|OCR Requests| GCV
    CeleryWorker -->|Entity Extraction & RAG| OpenAI
    DjangoCore -->|Direct Queries| VDB
    DjangoCore -->|Direct Chat| OpenAI
    CeleryWorker -->|Token Dispatch| SMS
```

---

## 2. Django Project Structure

MediVault uses a clean, domain-driven modular application structure located under `medivault/apps/`:

```
medivault/
├── manage.py
├── config/                         # Project settings & ASGI/WSGI entrypoints
│   ├── __init__.py
│   ├── asgi.py                     # ASGI config with ProtocolTypeRouter
│   ├── wsgi.py                     # Standard WSGI config
│   ├── urls.py                     # Root URL routing & Swagger docs
│   ├── celery.py                   # Celery application initialization
│   └── settings/
│       ├── __init__.py
│       ├── base.py                 # Core settings, installed apps, middleware
│       ├── development.py          # Local settings, debug toolbar
│       └── production.py           # Strict security, SSL, S3, connection pools
├── apps/
│   ├── accounts/                   # Custom User, phone verification, RBAC
│   ├── patients/                   # Patient profile, family member manager
│   ├── doctors/                    # Doctor profiles, chamber schedules
│   ├── clinics/                    # Clinic chamber registry, assistant profiles
│   ├── documents/                  # Document uploads, OCR pipeline, timeline
│   ├── health_logs/                # Blood glucose, BP, vitals, danger checks
│   ├── medications/                # Drug schedules, dose adherence, reminders
│   ├── prescriptions/              # Digital prescription writer, interaction checks
│   ├── appointments/               # Pre-booked visits, chamber queue, token dispatch
│   ├── sharing/                    # QR-code consultation handshake & audit logs
│   ├── ai_services/                # OpenAI client, RAG pipeline, ChromaDB sync
│   ├── reports/                    # Monthly health reports, PDF generators
│   ├── notifications/              # In-app alerts, SMS notification handlers
│   └── common/                     # Base models, custom permissions, utilities
├── media/                          # Uploaded medical scans and generated PDFs
├── static/                         # Static CSS/JS for Django admin and Swagger
└── templates/                      # Email and PDF report HTML templates
```

---

## 3. Data Flow Pipelines

### 3.1 Document Upload, OCR & Entity Extraction Pipeline

```mermaid
sequenceDiagram
    autonumber
    actor Patient
    participant API as Django API (/api/v1/documents/upload/)
    participant Storage as File Storage
    participant Queue as Redis / Celery
    participant OCR as Google Cloud Vision
    participant AI as OpenAI GPT-4o-mini
    participant DB as PostgreSQL
    participant VDB as ChromaDB

    Patient->>API: Multipart upload (image/pdf)
    API->>Storage: Validate MIME, size (<10MB), save file
    API->>DB: Create Document record (status='PENDING')
    API->>Queue: Dispatch task: process_document_ocr(doc_id)
    API-->>Patient: 202 Accepted (doc_id, status='PENDING')

    Note over Queue: Celery Worker picks up task
    Queue->>Storage: Retrieve image bytes
    Queue->>OCR: Annotate image (DOCUMENT_TEXT_DETECTION)
    OCR-->>Queue: Return raw OCR text block
    Queue->>DB: Update Document (raw_ocr_text, status='EXTRACTING')

    Queue->>AI: Send prompt with raw text + JSON entity schema
    AI-->>Queue: Return structured entities (Meds, Diagnoses, Lab Results)
    Queue->>DB: Save DocumentEntity records & update status='COMPLETED'

    Queue->>AI: Generate vector embeddings (text-embedding-3-small)
    AI-->>Queue: Return 1536-dimensional vector
    Queue->>VDB: Store embedding with metadata (patient_id, doc_id, date)
```

---

### 3.2 Daily Health Log Entry & Danger Alert Evaluation

```mermaid
sequenceDiagram
    autonumber
    actor Patient
    participant API as Health Logs API
    participant Engine as Danger Alert Engine (Django Signal)
    participant DB as PostgreSQL
    participant SMS as SMS Gateway
    participant WS as WebSocket Channel

    Patient->>API: POST /api/v1/health-logs/blood-glucose/ {value: 3.2, type: 'FASTING'}
    API->>DB: Save BloodGlucoseLog
    API->>Engine: Post-save signal triggered
    Engine->>Engine: Check threshold: 3.2 < 3.9 mmol/L (Hypoglycemia!)
    Engine->>DB: Create DangerAlert record (severity='CRITICAL', acknowledged=False)
    
    par Real-Time Alert to User
        Engine->>WS: Broadcast alert event to user's private notification channel
        WS-->>Patient: High-priority banner pops up with rescue instructions
    and Emergency SMS Backup
        Engine->>SMS: Dispatch SMS to patient / primary family contact
    end
    API-->>Patient: 201 Created (log data + danger_alert: true)
```

---

### 3.3 QR-Based Consultation Handshake & Session Expiration

```mermaid
sequenceDiagram
    autonumber
    actor Patient
    actor Doctor
    participant API as Django API
    participant Cache as Redis (Session Store)
    participant DB as PostgreSQL

    Patient->>API: POST /api/v1/sharing/qr/generate/
    API->>API: Generate cryptographically signed token (HMAC-SHA256)
    API->>Cache: Set key: qr_session:{token} -> {patient_id, scope} (TTL: 1800s)
    API-->>Patient: Return QR code SVG / payload token

    Doctor->>API: POST /api/v1/doctor/consultation/scan-qr/ {token}
    API->>Cache: Lookup qr_session:{token}
    alt Token Valid & Active
        API->>DB: Record ConsultationShare (doctor_id, patient_id, timestamp)
        API->>Cache: Create doctor_access_token (TTL: 1800s)
        API-->>Doctor: 200 OK (access_token, 90-day pre-consultation brief)
    else Token Expired or Invalid
        API-->>Doctor: 403 Forbidden ("QR token expired or already used")
    end
```

---

### 3.4 Real-Time Queue Synchronization (WebSocket)

```mermaid
sequenceDiagram
    autonumber
    actor Assistant
    actor Doctor
    actor Patient
    participant Daphne as ASGI Server (Daphne)
    participant Redis as Redis Channel Layer
    participant DB as PostgreSQL

    Assistant->>Daphne: PUT /api/v1/assistant/queue/14/status/ {status: 'CALLED_IN'}
    Daphne->>DB: Update QueueEntry record
    Daphne->>Redis: group_send("queue_clinic_5", type="queue.update", data)
    
    par Broadcast to Doctor
        Redis->>Daphne: Deliver to Doctor's active WebSocket connection
        Daphne-->>Doctor: WS Message: Token #14 marked CALLED_IN
    and Broadcast to Patient
        Redis->>Daphne: Deliver to Patient's active WebSocket connection
        Daphne-->>Patient: WS Message: Your Token #14 is CALLED IN!
    end
```

---

## 4. External Integrations Architecture

| External Service | Integration Purpose | Library / SDK | Failure & Fallback Strategy |
|---|---|---|---|
| **Google Cloud Vision** | Full-page OCR, handwriting detection | `google-cloud-vision` | Exponential backoff (3 retries). If OCR fails, flag document as `OCR_FAILED` and notify user for manual entry or image re-upload. |
| **OpenAI API** | Entity extraction, RAG embeddings, health summaries, drug interaction analysis | `openai>=1.30.0` | Circuit breaker pattern. Rate-limit (429) backoff. Fallback cached responses for standard drug queries. |
| **ChromaDB** | Vector similarity search for patient medical history queries | `chromadb-client` | Run ChromaDB container alongside PostgreSQL with persistent Docker volume storage. |
| **Bangladesh SMS Gateway** | OTP, Queue Token updates, Danger vitals alerts | Custom HTTP REST adapter (`httpx`) | Fallback to in-app push notifications if external SMS gateway responds with non-200. |

---

## 5. Security & Isolation Architecture

1. **Defense-in-Depth RBAC:**
   - Permissions are enforced strictly in Django ViewSet `permission_classes`.
   - Patients can only query objects where `patient = request.user.patient_profile`.
   - Doctors can only query patient data when an active, non-expired `ConsultationShare` exists in Redis or PostgreSQL.
2. **Data Minimization in QR Handshake:**
   - Scanned QR tokens only provide access to metadata, active medications, recent vitals, and last 3 consultation reports unless the patient explicitly checks "Full Medical Lifetime".
3. **Audit Trail Logging:**
   - Every file download, QR scan, and clinical record access is written to `ShareAuditLog` with IP address, user-agent, timestamp, and accessed document IDs.

