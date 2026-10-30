import logging
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Avg

from apps.appointments.models import Appointment, PreAppointmentSummary
from apps.health_logs.models import BloodGlucoseLog, BloodPressureLog, DangerAlert
from apps.medications.models import Medication
from apps.ai_services.openai_service import OpenAIService
from apps.ai_services.prompts import PRE_APPOINTMENT_SYNTHESIS_PROMPT

logger = logging.getLogger('medivault.appointments')

class IntakeSynthesizer:
    """
    Synthesizes the patient's 3-question intake responses with their 90-day vital statistics
    and current medication roster into a structured SOAP-style brief for the consulting doctor.
    """

    @classmethod
    def synthesize_pre_appointment_brief(
        cls,
        appointment: Appointment,
        primary_concern: str,
        reported_symptoms: str,
        medication_side_effects: str = ""
    ) -> PreAppointmentSummary:
        patient = appointment.patient
        ninety_days_ago = timezone.now() - timedelta(days=90)

        # 1. Deterministic clinical calculations
        glucose_logs = BloodGlucoseLog.objects.filter(patient=patient, recorded_at__gte=ninety_days_ago)
        avg_glucose = glucose_logs.aggregate(avg=Avg('glucose_value_mmol'))['avg']
        avg_glucose_str = f"{round(float(avg_glucose), 1)} mmol/L" if avg_glucose else "Not recorded"

        bp_logs = BloodPressureLog.objects.filter(patient=patient, recorded_at__gte=ninety_days_ago).order_by('-recorded_at')
        latest_bp = bp_logs.first()
        latest_bp_str = f"{latest_bp.systolic_mmHg}/{latest_bp.diastolic_mmHg} mmHg (Pulse: {latest_bp.pulse_bpm or 'N/A'} bpm)" if latest_bp else "Not recorded"

        danger_count = DangerAlert.objects.filter(patient=patient, created_at__gte=ninety_days_ago).count()

        active_meds = Medication.objects.filter(patient=patient, is_active=True)
        meds_list = [f"{m.name} {m.strength} ({m.dosage_pattern})" for m in active_meds]
        meds_str = ", ".join(meds_list) if meds_list else "None reported"

        # 2. Formulate synthesis prompt for GPT-4o-mini
        user_input = (
            f"PATIENT DETAILS:\n"
            f"Name: {patient.user.full_name}, Age/DOB: {patient.date_of_birth or 'N/A'}, Blood Group: {patient.blood_group}\n"
            f"Allergies: {patient.known_allergies or 'None reported'}\n\n"
            f"INTAKE RESPONSES:\n"
            f"1. Primary Concern: {primary_concern}\n"
            f"2. Recent Symptoms: {reported_symptoms}\n"
            f"3. Medication Side Effects: {medication_side_effects or 'None reported'}\n\n"
            f"90-DAY OBJECTIVE VITALS:\n"
            f"• 90-Day Glucose Average: {avg_glucose_str} ({glucose_logs.count()} logs)\n"
            f"• Latest BP: {latest_bp_str}\n"
            f"• Danger Alert Incidents (Last 90 Days): {danger_count}\n"
            f"• Active Medications: {meds_str}\n"
        )

        ai_brief = ""
        ai = OpenAIService()
        if ai.is_api_configured():
            try:
                from openai import OpenAI
                client = OpenAI(api_key=ai.api_key)
                res = client.chat.completions.create(
                    model=ai.model,
                    temperature=0.2,
                    messages=[
                        {"role": "system", "content": PRE_APPOINTMENT_SYNTHESIS_PROMPT},
                        {"role": "user", "content": user_input}
                    ]
                )
                ai_brief = res.choices[0].message.content.strip()
            except Exception as e:
                logger.error("Failed to generate AI intake synthesis with OpenAI: %s", str(e))

        if not ai_brief:
            # Fallback deterministic structured SOAP brief
            ai_brief = (
                f"S (Subjective):\n"
                f"• Chief Concern: {primary_concern}\n"
                f"• Reported Symptoms: {reported_symptoms}\n"
                f"• Side Effects: {medication_side_effects or 'None'}\n\n"
                f"O (Objective):\n"
                f"• 90-Day Glucose Average: {avg_glucose_str}\n"
                f"• Latest BP: {latest_bp_str}\n"
                f"• Active Medications: {meds_str}\n\n"
                f"A/P (Clinical Notes for Doctor):\n"
                f"• Patient scheduled for consultation. Review blood glucose control and symptom progression."
            )

        # 3. Create or update PreAppointmentSummary record
        summary, _ = PreAppointmentSummary.objects.update_or_create(
            appointment=appointment,
            defaults={
                "primary_concern": primary_concern,
                "reported_symptoms": reported_symptoms,
                "medication_side_effects": medication_side_effects,
                "ai_synthesized_brief": ai_brief,
            }
        )
        return summary

