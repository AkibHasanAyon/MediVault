# MediVault — REST & WebSocket API Specification

> **Base URL:** `https://api.medivault.app/api/v1`  
> **WebSocket Gateway:** `wss://api.medivault.app/ws`  
> **OpenAPI / Swagger Documentation UI:** `/api/docs/` (Interactive Swagger) & `/api/schema/` (Raw OpenAPI 3.1 YAML)  
> **Authentication Standard:** Bearer JWT Header (`Authorization: Bearer <access_token>`)

---

## 1. Global Conventions & Envelope Formats

### 1.1 Success Response Envelope
All successful requests return HTTP status codes `200 OK`, `201 Created`, or `204 No Content`. List endpoints include standard pagination metadata.

```json
{
  "success": true,
  "message": "Resource retrieved successfully",
  "data": { ... },
  "meta": {
    "page": 1,
    "page_size": 20,
    "total_records": 45,
    "total_pages": 3
  }
}
```

### 1.2 Error Response Envelope
```json
{
  "success": false,
  "error_code": "DANGER_THRESHOLD_TRIGGERED",
  "message": "Recorded blood glucose indicates critical hypoglycemia.",
  "errors": [
    {
      "field": "glucose_value_mmol",
      "detail": "Value 3.2 mmol/L is below safety threshold of 3.9 mmol/L."
    }
  ]
}
```

---

## 2. Authentication & User Endpoints (`/auth/`)

> **Messaging Channel Note:** MediVault supports dual delivery channels via `MESSAGING_BACKEND`. During development and prototyping, verification OTP codes are dispatched via **SMTP Email** (`MESSAGING_BACKEND=email`) to save third-party SMS costs. In live production, setting `MESSAGING_BACKEND=sms` routes OTPs to Bangladeshi phone carriers without altering frontend API request formats.

### 2.1 Register User
- **Method / URL:** `POST /api/v1/auth/register/`
- **Permissions:** AllowAny
- **Request Body:**
```json
{
  "phone_number": "+8801712345678",
  "email": "rafiqul.islam@example.com",
  "password": "SecurePassword#2026",
  "full_name": "Rafiqul Islam",
  "role": "PATIENT",
  "preferred_language": "bn"
}
```
- **Response (201 Created):**
```json
{
  "success": true,
  "message": "User registered successfully. Verification OTP dispatched via Email (MESSAGING_BACKEND=email).",
  "data": {
    "user_id": "a5d3f821-4f10-4821-bc30-7e3f890b0142",
    "phone_number": "+8801712345678",
    "email": "rafiqul.islam@example.com",
    "role": "PATIENT",
    "is_phone_verified": false,
    "otp_delivery_channel": "email"
  }
}
```

### 2.2 Verify OTP (Phone / Email)
- **Method / URL:** `POST /api/v1/auth/verify-phone/`
- **Request Body:**
```json
{
  "phone_number": "+8801712345678",
  "email": "rafiqul.islam@example.com",
  "otp_code": "849201"
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "message": "Identity successfully verified.",
  "data": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": "a5d3f821-4f10-4821-bc30-7e3f890b0142",
      "full_name": "Rafiqul Islam",
      "email": "rafiqul.islam@example.com",
      "phone_number": "+8801712345678",
      "role": "PATIENT"
    }
  }
}
```

### 2.3 Resend Verification OTP
- **Method / URL:** `POST /api/v1/auth/resend-otp/`
- **Permissions:** AllowAny (Throttled: max 3/5min)
- **Request Body:**
```json
{
  "phone_number": "+8801712345678",
  "email": "rafiqul.islam@example.com"
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "message": "Fresh 6-digit OTP code dispatched.",
  "data": {
    "resend_countdown_seconds": 60,
    "channel": "email"
  }
}
```

### 2.4 User Login
- **Method / URL:** `POST /api/v1/auth/login/`
- **Request Body:**
```json
{
  "phone_number": "+8801712345678",
  "password": "SecurePassword#2026"
}
```
- **Response (200 OK):** Returns new `access` and `refresh` tokens plus role context.

---

## 3. Patient Endpoints

### 3.1 Document Upload & Processing
- **Method / URL:** `POST /api/v1/documents/upload/`
- **Content-Type:** `multipart/form-data`
- **Permissions:** IsAuthenticated, IsPatient
- **Form Data:**
  - `file`: `prescription_dr_nasreen.jpg` (Binary Image/PDF)
  - `document_type`: `PRESCRIPTION`
  - `document_date`: `2026-08-14`
  - `family_member_id`: `null` (Optional UUID)
- **Response (202 Accepted):**
```json
{
  "success": true,
  "message": "Document accepted for background OCR and entity extraction.",
  "data": {
    "document_id": "7c1b5049-e314-411a-a128-4f24f5a2b160",
    "status": "PROCESSING_OCR",
    "document_type": "PRESCRIPTION",
    "file_url": "https://api.medivault.app/media/patient_documents/2026/08/scan.jpg"
  }
}
```

### 3.2 Get Document Detail with Extracted Clinical Entities
- **Method / URL:** `GET /api/v1/documents/{document_id}/`
- **Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "7c1b5049-e314-411a-a128-4f24f5a2b160",
    "title": "Prescription from Dr. Nasreen Akhter",
    "document_date": "2026-08-14",
    "issuing_doctor": "Prof. Dr. Nasreen Akhter",
    "issuing_clinic": "Green Life Medical Chambers",
    "processing_status": "COMPLETED",
    "extracted_entities": [
      {
        "type": "DIAGNOSIS",
        "name": "Type 2 Diabetes Mellitus"
      },
      {
        "type": "DIAGNOSIS",
        "name": "Primary Essential Hypertension"
      },
      {
        "type": "MEDICATION",
        "name": "Tab. Metformin",
        "strength": "500mg",
        "frequency": "1+0+1",
        "timing": "After Food",
        "duration": "90 days"
      },
      {
        "type": "MEDICATION",
        "name": "Tab. Telmisartan",
        "strength": "40mg",
        "frequency": "0+0+1",
        "timing": "Bedtime",
        "duration": "90 days"
      }
    ]
  }
}
```

### 3.3 Log Blood Glucose
- **Method / URL:** `POST /api/v1/health-logs/blood-glucose/`
- **Request Body:**
```json
{
  "glucose_value_mmol": 3.4,
  "reading_type": "FASTING",
  "recorded_at": "2026-10-29T07:30:00+06:00",
  "notes": "Felt cold sweat and tremors before breakfast."
}
```
- **Response (201 Created):**
```json
{
  "success": true,
  "message": "Health vital recorded.",
  "data": {
    "id": "893c5d6e-01a2-41e9-9a28-6e54f73b841a",
    "glucose_value_mmol": 3.4,
    "reading_type": "FASTING",
    "danger_alert": {
      "triggered": true,
      "severity": "CRITICAL",
      "type": "HYPOGLYCEMIA",
      "instructions": "Take 15g fast-acting carbohydrate immediately (1/2 cup juice or 3 candies). Recheck in 15 mins."
    }
  }
}
```

### 3.4 Ask AI — Query Personal Medical Records (RAG)
- **Method / URL:** `POST /api/v1/ai/ask/`
- **Request Body:**
```json
{
  "question": "আমার শেষ প্রেসক্রিপশনে ডাক্তার কোন অ্যান্টিবায়োটিক লিখেছিলেন?",
  "language": "bn",
  "family_member_id": null
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "answer": "আপনার সর্বশেষ আপলোড করা প্রেসক্রিপশন (তারিখ: ১৪ আগস্ট ২০২৬, ডাক্তার: প্রফেসর নাসরিন আক্তার) অনুসারে কোনো অ্যান্টিবায়োটিক প্রেসক্রাইব করা হয়নি। প্রেসক্রিপশনে ডায়াবেটিসের জন্য ট্যাব. মেটফর্মিন ৫০০ মিগ্রা (১+০+১) এবং রক্তচাপের জন্য ট্যাব. টেলমিসারটান ৪০ মিগ্রা (০+০+১) রয়েছে।",
    "citations": [
      {
        "document_id": "7c1b5049-e314-411a-a128-4f24f5a2b160",
        "title": "Prescription - Dr. Nasreen Akhter (14 Aug 2026)",
        "snippet": "Tab. Metformin 500mg (1+0+1), Tab. Telmisartan 40mg (0+0+1)..."
      }
    ],
    "disclaimer": "MediVault AI helps organize and query existing records. It does not provide medical diagnosis or replace physician consultation."
  }
}
```

### 3.5 Generate Ephemeral Consultation QR Code
- **Method / URL:** `POST /api/v1/sharing/qr/generate/`
- **Request Body:**
```json
{
  "scope": "LAST_90_DAYS",
  "include_family_member_id": null
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "token": "mv_share_7b9a28c014ef9081e6",
    "expires_at": "2026-10-29T19:15:00+06:00",
    "duration_seconds": 1800,
    "qr_data_string": "medivault://consultation/handshake?token=mv_share_7b9a28c014ef9081e6"
  }
}
```

---

## 4. Doctor Endpoints

### 4.1 Scan QR & Unlock Patient Clinical Brief
- **Method / URL:** `POST /api/v1/doctor/consultation/scan-qr/`
- **Permissions:** IsAuthenticated, IsDoctor
- **Request Body:**
```json
{
  "qr_token": "mv_share_7b9a28c014ef9081e6"
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "message": "Consultation handshake established.",
  "data": {
    "patient": {
      "id": "a5d3f821-4f10-4821-bc30-7e3f890b0142",
      "full_name": "Rafiqul Islam",
      "age": 54,
      "gender": "MALE",
      "blood_group": "B+"
    },
    "ai_pre_consultation_brief": {
      "glucose_90_day_avg_mmol": 8.4,
      "glucose_fasting_avg": 7.1,
      "glucose_post_meal_avg": 9.6,
      "bp_90_day_avg": "138/86 mmHg",
      "active_medications": [
        {"name": "Metformin 500mg", "adherence_rate": "92%"},
        {"name": "Telmisartan 40mg", "adherence_rate": "88%"}
      ],
      "flagged_anomalies": [
        "1 episode of severe hypoglycemia (3.4 mmol/L) logged on 29 Oct 2026.",
        "Serum Creatinine 1.3 mg/dL on last lab test (14 Aug 2026) - slightly elevated."
      ]
    }
  }
}
```

### 4.2 Check Drug-Drug Interactions
- **Method / URL:** `POST /api/v1/doctor/prescriptions/check-interactions/`
- **Request Body:**
```json
{
  "patient_id": "a5d3f821-4f10-4821-bc30-7e3f890b0142",
  "prescribed_drugs": [
    {"name": "Metformin", "strength": "500mg"},
    {"name": "Ciprofloxacin", "strength": "500mg"},
    {"name": "Telmisartan", "strength": "40mg"}
  ]
}
```
- **Response (200 OK):**
```json
{
  "success": true,
  "has_interactions": true,
  "interactions": [
    {
      "severity": "MODERATE",
      "drug_1": "Ciprofloxacin",
      "drug_2": "Metformin",
      "description": "Quinolone antibiotics may enhance the hypoglycemic effect of Metformin. Monitor blood glucose closely."
    }
  ]
}
```

### 4.3 Issue Digital Prescription
- **Method / URL:** `POST /api/v1/doctor/prescriptions/`
- **Request Body:**
```json
{
  "patient_id": "a5d3f821-4f10-4821-bc30-7e3f890b0142",
  "chief_complaints": "Frequent urination, fatigue, occasional dizziness.",
  "diagnosis": "Type 2 Diabetes Mellitus (Uncontrolled), Essential Hypertension",
  "medications": [
    {
      "brand_name": "Comet",
      "generic_name": "Metformin Hydrochloride",
      "strength": "850mg",
      "frequency": "1+0+1",
      "timing_relation": "After Food",
      "duration_days": 90,
      "special_instructions": "Take immediately after lunch and dinner."
    }
  ],
  "investigations_ordered": [
    "HbA1c",
    "Serum Creatinine",
    "Urine R/M/E"
  ],
  "follow_up_date": "2026-11-29",
  "follow_up_notes": "Review after 1 month with test reports."
}
```
- **Response (201 Created):** Returns generated prescription record with PDF download URL. Instantly creates medication schedules in the patient's app.

---

## 5. Clinic Assistant Endpoints

### 5.1 Assign Queue Token
- **Method / URL:** `POST /api/v1/assistant/queue/assign-token/`
- **Permissions:** IsAuthenticated, IsClinicAssistant
- **Request Body:**
```json
{
  "doctor_id": "b3f12450-8192-4f31-89a1-5d9c2810a931",
  "patient_phone": "+8801712345678",
  "patient_name": "Rafiqul Islam",
  "appointment_id": null
}
```
- **Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "token_number": 14,
    "patient_name": "Rafiqul Islam",
    "state": "WAITING",
    "estimated_wait_minutes": 25,
    "sms_dispatched": true
  }
}
```

### 5.2 Update Queue Status
- **Method / URL:** `PUT /api/v1/assistant/queue/{queue_id}/status/`
- **Request Body:**
```json
{
  "state": "CALLED_IN"
}
```
- **Response (200 OK):** Broadcasts real-time update to doctor and patient via WebSocket.

---

## 6. Real-Time WebSocket Specifications

### 6.1 Connect to Clinic Queue Feed
- **URL:** `wss://api.medivault.app/ws/queue/{clinic_id}/`
- **Headers:** `Authorization: Bearer <jwt_token>`
- **Outgoing Event from Client:** None (listen-only feed).
- **Incoming Broadcast Event (Queue Shift):**
```json
{
  "type": "queue.update",
  "timestamp": "2026-10-29T18:45:00Z",
  "payload": {
    "doctor_id": "b3f12450-8192-4f31-89a1-5d9c2810a931",
    "current_token_in_chamber": 13,
    "next_token_called": 14,
    "waiting_patient_count": 7,
    "estimated_wait_per_patient_min": 6
  }
}
```

### 6.2 Connect to User Notification Feed
- **URL:** `wss://api.medivault.app/ws/notifications/{user_id}/`
- **Incoming Broadcast Event (Danger Alert):**
```json
{
  "type": "notification.danger_alert",
  "payload": {
    "alert_id": "893c5d6e-01a2-41e9-9a28-6e54f73b841a",
    "alert_type": "HYPOGLYCEMIA",
    "value": "3.4 mmol/L",
    "message": "Critical hypoglycemia detected. Immediate sugar intake needed."
  }
}
```

---

## 7. Swagger / OpenAPI Integration (`drf-spectacular`)

In `medivault/config/settings/base.py`:
```python
INSTALLED_APPS += ['drf_spectacular']

REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'

SPECTACULAR_SETTINGS = {
    'TITLE': 'MediVault Clinical Platform API',
    'DESCRIPTION': 'AI-Powered Personal Health Record & Doctor Communication Platform',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
}
```

In `medivault/config/urls.py`:
```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
```

