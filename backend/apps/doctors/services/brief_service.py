import logging
from datetime import timedelta
from django.utils import timezone
from django.core.cache import cache
from django.db.models import Avg

from apps.patients.models import PatientProfile
from apps.health_logs.models import BloodGlucoseLog, BloodPressureLog, DangerAlert
from apps.medications.models import Medication
from apps.documents.models import MedicalDocument
from apps.ai_services.openai_service import OpenAIService
from apps.ai_services.prompts import DOCTOR_BRIEF_SYNTHESIS_PROMPT

logger = logging.getLogger('medivault.doctor')

class DoctorBriefService:
    """
    Synthesizes a high-yield, 10-second chamber consultation brief for attending doctors.
    Combines deterministic 90-day vital stats, danger alerts, medication roster,
    and a 3-bullet AI synthesis. Caches results in Redis with a 10-minute TTL.
    """

    CACHE_TTL_SECONDS = 600  # 10 minutes

    @classmethod
    def get_patient_brief(cls, patient_id: str, force_refresh: bool = False) -> dict:
        cache_key = f"doctor_patient_brief_{patient_id}"

        if not force_refresh:
            cached_data = cache.get(cache_key)
            if cached_data:
                logger.info("Serving doctor brief for patient %s from cache", patient_id)
                cached_data["is_cached"] = True
                return cached_data

        try:
            patient = PatientProfile.objects.select_related('user').get(id=patient_id)
        except PatientProfile.DoesNotExist:
            return {"error": "Patient profile not found."}

        ninety_days_ago = timezone.now() - timedelta(days=90)

        # 1. Deterministic 90-day vitals
        glucose_logs = BloodGlucoseLog.objects.filter(patient=patient, recorded_at__gte=ninety_days_ago)
        avg_glucose = glucose_logs.aggregate(avg=Avg('glucose_value_mmol'))['avg']
        avg_glucose_val = round(float(avg_glucose), 1) if avg_glucose else None

        latest_bp = BloodPressureLog.objects.filter(patient=patient, recorded_at__gte=ninety_days_ago).order_by('-recorded_at').first()
        bp_reading = f"{latest_bp.systolic_mmHg}/{latest_bp.diastolic_mmHg} mmHg" if latest_bp else "Not recorded"
        bp_stage = "NORMAL"
        if latest_bp:
            if latest_bp.systolic_mmHg > 180 or latest_bp.diastolic_mmHg > 120:
                bp_stage = "HYPERTENSIVE_CRISIS"
            elif latest_bp.systolic_mmHg >= 140 or latest_bp.diastolic_mmHg >= 90:
                bp_stage = "STAGE_2_HYPERTENSION"
            elif latest_bp.systolic_mmHg >= 130 or latest_bp.diastolic_mmHg >= 80:
                bp_stage = "STAGE_1_HYPERTENSION"

        danger_count = DangerAlert.objects.filter(patient=patient, created_at__gte=ninety_days_ago).count()

        # 2. Active medications
        active_meds = Medication.objects.filter(patient=patient, is_active=True)
        meds_summary = [
            {
                "name": m.name,
                "strength": m.strength,
                "dosage_pattern": m.dosage_pattern,
                "refill_remaining_doses": m.refill_remaining_doses
            }
            for m in active_meds
        ]

        # 3. Recent documents
        recent_docs = MedicalDocument.objects.filter(patient=patient).order_by('-document_date')[:3]
        docs_summary = [
            {"id": str(d.id), "title": d.title, "type": d.document_type, "date": str(d.document_date)}
            for d in recent_docs
        ]

        # 4. Synthesize 3-bullet clinical summary via GPT-4o-mini
        user_prompt = (
            f"Patient: {patient.user.full_name}, Age/DOB: {patient.date_of_birth or 'N/A'}, Blood: {patient.blood_group}\n"
            f"Allergies: {patient.known_allergies or 'None reported'}\n"
            f"90-Day Glucose Average: {avg_glucose_val or 'N/A'} mmol/L ({glucose_logs.count()} logs)\n"
            f"Latest Blood Pressure: {bp_reading} (Stage: {bp_stage})\n"
            f"Danger Alert Incidents (Last 90 Days): {danger_count}\n"
            f"Active Medications: {[m['name'] + ' ' + m['strength'] for m in meds_summary]}\n"
            f"Recent Documents: {[d['title'] + ' (' + str(d['date']) + ')' for d in docs_summary]}\n"
        )

        ai_bullets = []
        ai = OpenAIService()
        if ai.is_api_configured():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=ai.api_key)
                res = client.chat.completions.create(
                    model=ai.model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": DOCTOR_BRIEF_SYNTHESIS_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ]
                )
                text = res.choices[0].message.content.strip()
                ai_bullets = [b.strip() for b in text.split('\n') if b.strip()]
            except Exception as e:
                logger.error("Failed to generate doctor brief AI synthesis: %s", str(e))

        if not ai_bullets:
            # Deterministic fallback bullets
            ai_bullets = [
                f"• 90-Day Glucose Control: {avg_glucose_val or 'No recent readings'} mmol/L; BP: {bp_reading} ({bp_stage}).",
                f"• Active Medications: {len(meds_summary)} drug(s) on file with {danger_count} danger incident(s) in last 90 days.",
                f"• Recent Records: {len(docs_summary)} medical document(s) uploaded on file for review today."
            ]

        brief_payload = {
            "patient_id": str(patient.id),
            "patient_name": patient.user.full_name,
            "patient_phone": patient.user.phone_number,
            "blood_group": patient.blood_group,
            "known_allergies": patient.known_allergies,
            "glucose_90_day_avg_mmol": avg_glucose_val,
            "latest_bp": bp_reading,
            "bp_stage": bp_stage,
            "danger_alerts_count_90d": danger_count,
            "active_medications": meds_summary,
            "recent_documents": docs_summary,
            "ai_three_bullet_summary": ai_bullets,
            "generated_at": timezone.now().isoformat(),
            "is_cached": False,
        }

        cache.set(cache_key, brief_payload, cls.CACHE_TTL_SECONDS)
        logger.info("Generated and cached fresh doctor brief for patient %s", patient_id)
        return brief_payload

