# MediVault — Feature Development Blueprint

> **Engineering Scope:** 14 Primary Features across Patient, Doctor, and Clinic Assistant Applications  
> **Backend Architecture:** Django 5.x REST Framework + Django Channels + Celery 5.x  
> **Frontend Architecture:** React 18 + Vite + Tailwind CSS + Lucide Icons

---

## 1. Feature Specification Blueprint Template

Each feature in this guide is documented with the following rigorous technical blueprint:
- **Feature Name & Functional Scope**
- **User Stories & Acceptance Criteria**
- **Django Models Involved**
- **Serializer Specifications**
- **API Views & ViewSet Implementation**
- **Permissions & Security Guardrails**
- **Celery Tasks / Async Processing (if applicable)**
- **Frontend Components Needed**
- **Testing & Verification Scenarios**

---

## 2. The 14 Core Features

### Feature 1: User Registration & Phone Verification (Onboarding)
- **Scope:** Phone and email registration, dual-channel OTP dispatch via `MessagingService` (SMTP Email during development/prototyping, SMS gateway in production), role selection (`PATIENT`, `DOCTOR`, `ASSISTANT`), and initial profile completion.
- **User Story:** *As a user in Bangladesh, I want to sign up using my phone number and email to receive a 6-digit OTP code to securely verify my identity without friction.*
- **Models:** `User` (`phone_number`, `email`, `role`, `is_phone_verified`), `PatientProfile` / `DoctorProfile` / `ClinicAssistantProfile`.
- **Serializers:** `UserRegistrationSerializer`, `PhoneVerificationSerializer`, `UserProfileSerializer`.
- **Key Views:**
  - `POST /api/v1/auth/register/` (dispatches 6-digit OTP via Email or SMS depending on `MESSAGING_BACKEND`)
  - `POST /api/v1/auth/verify-phone/` (validates OTP, sets `is_phone_verified=True`, returns JWT pair)
  - `POST /api/v1/auth/resend-otp/` (rate-limited code re-dispatch)
  - `GET /api/v1/auth/me/` (profile hydration)
- **Frontend Components:** `PhoneInputStep.tsx`, `OTPVerificationStep.tsx`, `RoleSelectorCard.tsx`, `OnboardingWizard.tsx`.
- **Verification:** Test registration with valid Bangladeshi phone format (`+88017XXXXXXXX`); verify OTP code received via configured SMTP inbox; test invalid code rejection; verify OTP timeout (5 minutes).

---

### Feature 2: Document Upload & AI Entity Extraction Pipeline
- **Scope:** Ingest camera capture / multi-page PDF, execute Google Cloud Vision OCR, extract medications/diagnoses via GPT-4o-mini, and render in timeline.
- **User Story:** *As a patient, I want to snap a photo of my doctor's prescription so that its medications, doses, and test results are automatically read and organized.*
- **Models:** `MedicalDocument`, `DocumentEntity`.
- **Serializers:** `MedicalDocumentSerializer`, `DocumentEntitySerializer`.
- **Key Views:**
  - `POST /api/v1/documents/upload/` (multipart form parser, returns 202 Accepted)
  - `GET /api/v1/documents/{id}/` (detail with nested extracted entities)
  - `GET /api/v1/documents/timeline/` (chronological list with filters)
- **Celery Task:** `process_document_ocr_task` (runs image preprocessing, GCP Vision call, GPT-4o-mini entity schema parsing, ChromaDB vector indexing).
- **Frontend Components:** `CameraCaptureModal.tsx`, `DocumentTimelineCard.tsx`, `EntityChipList.tsx`, `RawOCRViewerModal.tsx`.
- **Verification:** Upload a 300dpi handwritten prescription JPEG; verify extracted `DocumentEntity` rows contain correct brand names, strengths, and dosage patterns.

---

### Feature 3: Daily Health Logging (Vitals)
- **Scope:** Recording blood glucose (fasting, post-meal, bedtime), blood pressure (systolic, diastolic, pulse), weight, and symptoms.
- **User Story:** *As a diabetic patient, I want to record my morning fasting sugar and evening blood pressure so I can track trends over time.*
- **Models:** `BloodGlucoseLog`, `BloodPressureLog`, `WeightLog`, `SymptomNote`.
- **Serializers:** `BloodGlucoseLogSerializer`, `BloodPressureLogSerializer`.
- **Key Views:**
  - `POST /api/v1/health-logs/blood-glucose/`
  - `GET /api/v1/health-logs/blood-glucose/?period=30d`
  - `POST /api/v1/health-logs/blood-pressure/`
  - `GET /api/v1/health-logs/trends/?metric=glucose`
- **Frontend Components:** `QuickLogModal.tsx`, `GlucoseMetricCard.tsx`, `BPTrendChart.tsx`, `SymptomTagsInput.tsx`.
- **Verification:** Verify that fasting reading 5.4 mmol/L saves with `is_danger=False`; verify query aggregation calculates accurate 7/30/90-day averages.

---

### Feature 4: Algorithmic Danger Alert Engine
- **Scope:** Automated detection of severe vital anomalies with real-time UI banners and emergency dispatch (Email in dev/prototype, SMS in live production).
- **Thresholds:**
  - Hypoglycemia: `< 3.9 mmol/L`
  - Hyperglycemia: `> 16.0 mmol/L`
  - Hypertensive Crisis: `Systolic > 180 or Diastolic > 120 mmHg`
- **User Story:** *As a patient with severe hypoglycemia, I want an immediate warning with emergency sugar intake instructions so I do not faint.*
- **Models:** `DangerAlert`.
- **Signals / Tasks:** `check_blood_glucose_danger` signal triggers `send_emergency_alert_task` (routed through `MessagingService` via SMTP Email or SMS) and publishes to WebSocket channel `user_{id}_alerts`.
- **Frontend Components:** `DangerAlertBanner.tsx` (pulsing red header with 1-tap call button).
- **Verification:** POST glucose value 3.1 mmol/L; verify `DangerAlert` created, WebSocket notification received in `< 200ms`, alert notification task queued.

---

### Feature 5: Medication Management & Adherence Tracker
- **Scope:** Medication schedule populated automatically from digital prescriptions or OCR, daily dose reminders, adherence logging, refill counter.
- **User Story:** *As a hypertensive patient, I want daily alerts at 8:00 AM and 9:00 PM reminding me to take my tablets with a "Taken" button.*
- **Models:** `Medication`, `MedicationReminder`, `MedicationAdherence`.
- **Key Views:**
  - `GET /api/v1/medications/` (active medications list)
  - `PUT /api/v1/medications/{id}/adherence/` (action: `TAKEN`, `SKIPPED`, `SNOOZED`)
  - `GET /api/v1/medications/today-schedule/`
- **Celery Beat Schedule:** `dispatch_daily_medication_reminders` runs every 15 minutes checking for scheduled doses.
- **Frontend Components:** `DailyMedsDoseCard.tsx`, `TakenButtonToggle.tsx`, `RefillAlertBadge.tsx`.
- **Verification:** Mark medication taken; verify adherence percentage recalculates and remaining refill dose decrements by 1.

---

### Feature 6: Ask AI — Conversational Health Records Explorer (RAG)
- **Scope:** Bilingual (Bangla + English) conversational Q&A over patient's uploaded documents and general health knowledge.
- **User Story:** *As a patient, I want to ask "গত মাসে ডাক্তার আমাকে কি গ্যাস্ট্রিকের ওষুধ দিয়েছিলেন?" and receive a cited answer in Bengali.*
- **Models:** `AIConversation`, `AIMessage`.
- **Architecture:** ChromaDB vector similarity search retrieving top 4 document chunks + GPT-4o-mini grounded prompt.
- **Key Views:**
  - `POST /api/v1/ai/ask/`
  - `GET /api/v1/ai/conversations/`
- **Frontend Components:** `AIChatDrawer.tsx`, `ChatMessageBubble.tsx`, `CitationPill.tsx`, `DisclaimerFooter.tsx`.
- **Verification:** Query document mentioning "Tab. Nexum 20mg"; verify answer identifies drug name and links directly to the cited prescription PDF.

---

### Feature 7: Pre-Appointment 3-Question Intake Synthesis
- **Scope:** Guided 3-question intake before clinical visits, aggregated with 90-day vitals into a 1-page digital brief.
- **User Story:** *As a patient visiting Dr. Nasreen tomorrow, I want to fill in my main problem and side effects so the doctor is fully prepared.*
- **Models:** `PreAppointmentSummary`.
- **Key Views:**
  - `POST /api/v1/appointments/{id}/pre-summary/`
  - `GET /api/v1/appointments/{id}/pre-summary/`
- **Frontend Components:** `PreAppointmentIntakeWizard.tsx`, `DoctorClinicalBriefView.tsx`.
- **Verification:** Submit 3 questions; verify GPT-4o-mini outputs structured 4-part summary (Subjective, Objective, Meds, Focus Areas).

---

### Feature 8: Automated Monthly Health Report (PDF)
- **Scope:** Monthly clinical overview generated on the 1st of each calendar month with trends, adherence score, AI narrative, and PDF export.
- **User Story:** *As a caregiver, I want a monthly PDF report summarizing my father's diabetes control so I can show it to his endocrinologist.*
- **Models:** `MonthlyHealthReport`.
- **Celery Beat:** `generate_all_monthly_reports_task` runs on the 1st at 00:00 UTC.
- **PDF Engine:** `weasyprint` converting dynamic HTML template to vector PDF with embedded SVG charts.
- **Key Views:**
  - `GET /api/v1/reports/monthly/`
  - `GET /api/v1/reports/monthly/{id}/pdf/`
- **Frontend Components:** `MonthlyReportViewer.tsx`, `DownloadPDFButton.tsx`, `AdherenceScoreGauge.tsx`.

---

### Feature 9: Ephemeral QR Consultation Handshake
- **Scope:** Dynamic QR generation on patient phone; scanning by doctor app unlocks temporary 30-minute read-only access.
- **User Story:** *As a patient entering the doctor's room, I want to show a QR code on my screen so the doctor can instantly see my medical file without logging into my account.*
- **Models:** `ConsultationShare`, `ShareAuditLog`.
- **Security:** HMAC-SHA256 signed tokens stored in Redis with 1800-second TTL.
- **Key Views:**
  - `POST /api/v1/sharing/qr/generate/` (patient)
  - `POST /api/v1/doctor/consultation/scan-qr/` (doctor)
  - `DELETE /api/v1/sharing/{id}/revoke/` (patient)
- **Frontend Components:** `QRHandshakeModal.tsx`, `DoctorQRScannerView.tsx`.
- **Verification:** Generate QR, scan with doctor account, verify doctor can view patient's timeline; wait 31 minutes, verify access returns 403 Forbidden.

---

### Feature 10: Digital Prescription Writer & Drug Interaction Safeguard
- **Scope:** Fast in-app prescription generator for doctors with typeahead medication database and real-time drug interaction checks.
- **User Story:** *As a doctor, I want to create a clean digital prescription and have the system warn me if I prescribe a drug that interacts with the patient's existing pills.*
- **Models:** `Prescription`, `PrescriptionMedication`, `DrugInteraction`.
- **Key Views:**
  - `POST /api/v1/doctor/prescriptions/check-interactions/`
  - `POST /api/v1/doctor/prescriptions/`
  - `GET /api/v1/doctor/prescriptions/{id}/pdf/`
- **Frontend Components:** `PrescriptionCanvas.tsx`, `MedicationTypeaheadInput.tsx`, `InteractionWarningDialog.tsx`.
- **Verification:** Enter Metformin + Ciprofloxacin; verify modal warns of potential hypoglycemia enhancement; verify finalized prescription appears in patient's app within 1 second.

---

### Feature 11: Real-Time Chamber Queue Management & Serial Notifications
- **Scope:** Live queue synchronization between clinic assistant, doctor, and patient devices via WebSockets, with automated token notifications (Email in dev/prototype, SMS in live production via `MessagingService`).
- **User Story:** *As a clinic assistant, I want to issue serial tokens and click "Call In" so that both the doctor's screen and the patient's phone update simultaneously.*
- **Models:** `QueueEntry`, `Appointment`.
- **WebSocket:** Django Channels consumer `ClinicQueueConsumer` broadcasting to `queue_clinic_{id}`.
- **Key Views:**
  - `POST /api/v1/assistant/queue/assign-token/`
  - `PUT /api/v1/assistant/queue/{id}/status/` (dispatches notification via `MessagingService`)
  - `GET /api/v1/assistant/queue/today/`
- **Frontend Components:** `QueueBoardTable.tsx`, `TokenAssignmentDrawer.tsx`, `LiveChamberBadge.tsx`.
- **Verification:** Update token status from assistant desktop; verify doctor UI switches active patient card without page refresh (< 300ms latency); verify notification email dispatched in dev environment.

---

### Feature 12: Family Health Manager (Multi-Profile)
- **Scope:** Single phone account managing dependent family members (elderly parents, children) with isolated document vaults and logs.
- **User Story:** *As a son managing my diabetic father and hypertensive mother, I want to switch between their profiles in one tap.*
- **Models:** `FamilyMember`.
- **Key Views:**
  - `GET /api/v1/patients/family-members/`
  - `POST /api/v1/patients/family-members/`
  - `GET /api/v1/patients/family-members/{id}/timeline/`
- **Frontend Components:** `FamilyProfileSwitcher.tsx`, `AddMemberModal.tsx`.
- **Verification:** Add family member "Father"; upload document tagged with father's ID; verify document does not appear in mother's filtered timeline.

---

### Feature 13: Doctor Patient Registry & 10-Second Brief
- **Scope:** Longitudinal patient directory for doctors, with rapid search by phone/name and 1-click 10-second clinical synthesis.
- **User Story:** *As a doctor, I want to search for a returning patient by phone number and immediately review their 90-day glucose chart and past visits.*
- **Key Views:**
  - `GET /api/v1/doctor/patients/?q=+8801712345678`
  - `GET /api/v1/doctor/patients/{id}/brief/`
- **Frontend Components:** `PatientRegistryTable.tsx`, `TenSecondClinicalBrief.tsx`, `PastPrescriptionsAccordion.tsx`.
- **Verification:** Search patient by phone number; verify all past digital prescriptions and uploaded reports ordered by this doctor are displayed.

---

### Feature 14: Smart Appointment Scheduling & Escalated Reminders
- **Scope:** Chamber appointment booking, return visit tracking extracted from prescriptions, and multi-stage reminder escalation (2.5 months → 1 week → due date).
- **User Story:** *As a patient advised to see the doctor in 3 months, I want reminder alerts leading up to the due date so I don't forget my checkup.*
- **Models:** `Appointment`, `FollowUpReminder`.
- **Celery Beat:** `check_follow_up_escalations` runs daily at 09:00 AM.
- **Key Views:**
  - `POST /api/v1/appointments/`
  - `GET /api/v1/appointments/my-appointments/`
- **Frontend Components:** `ChamberBookingCalendar.tsx`, `AppointmentTicketCard.tsx`, `FollowUpCountdownPill.tsx`.
- **Verification:** Create prescription with "Review after 3 months"; verify `FollowUpReminder` records created with scheduled trigger dates at +75 days, +83 days, and +90 days.

