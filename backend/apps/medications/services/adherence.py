from datetime import date, timedelta
from typing import Dict, Any
from django.utils import timezone
from apps.medications.models import Medication, MedicationAdherence

class AdherenceEngine:
    """
    Computes medication adherence analytics and provides clinically compliant
    guidance for missed or delayed doses.
    """

    SAFEGUARD_MISSED_DOSE_WARNING = (
        "Never take a double or extra dose to make up for a missed dose. "
        "Take the next dose at your regularly scheduled time. "
        "Consult your physician or pharmacist if you missed multiple consecutive doses."
    )

    @classmethod
    def calculate_medication_adherence(cls, medication: Medication, days: int = 30) -> Dict[str, Any]:
        """
        Calculates adherence percentage for a single active medication over the last N days.
        Formula: (Taken Doses / Total Recorded Adherence Entries) * 100
        """
        since_date = timezone.now() - timedelta(days=days)
        logs = medication.adherence_logs.filter(scheduled_time__gte=since_date)

        total_scheduled = logs.count()
        taken_count = logs.filter(action=MedicationAdherence.Action.TAKEN).count()
        skipped_count = logs.filter(action=MedicationAdherence.Action.SKIPPED).count()
        snoozed_count = logs.filter(action=MedicationAdherence.Action.SNOOZED).count()

        adherence_percentage = 0.0
        if total_scheduled > 0:
            adherence_percentage = round((taken_count / total_scheduled) * 100.0, 1)

        return {
            "medication_id": str(medication.id),
            "medication_name": medication.name,
            "period_days": days,
            "total_logged_doses": total_scheduled,
            "taken_count": taken_count,
            "skipped_count": skipped_count,
            "snoozed_count": snoozed_count,
            "adherence_percentage": adherence_percentage,
            "clinical_safeguard": cls.SAFEGUARD_MISSED_DOSE_WARNING,
        }

    @classmethod
    def calculate_overall_patient_adherence(cls, patient, days: int = 30) -> Dict[str, Any]:
        """
        Calculates aggregate adherence rate across all active medications for a patient.
        """
        active_meds = Medication.objects.filter(patient=patient, is_active=True)
        if not active_meds.exists():
            return {
                "period_days": days,
                "active_medications_count": 0,
                "overall_adherence_percentage": 100.0,
                "total_doses_taken": 0,
                "total_doses_scheduled": 0,
                "clinical_safeguard": cls.SAFEGUARD_MISSED_DOSE_WARNING,
            }

        since_date = timezone.now() - timedelta(days=days)
        logs = MedicationAdherence.objects.filter(
            medication__patient=patient,
            medication__is_active=True,
            scheduled_time__gte=since_date
        )

        total_scheduled = logs.count()
        taken_count = logs.filter(action=MedicationAdherence.Action.TAKEN).count()
        skipped_count = logs.filter(action=MedicationAdherence.Action.SKIPPED).count()

        overall_percentage = 0.0
        if total_scheduled > 0:
            overall_percentage = round((taken_count / total_scheduled) * 100.0, 1)

        return {
            "period_days": days,
            "active_medications_count": active_meds.count(),
            "overall_adherence_percentage": overall_percentage,
            "total_doses_taken": taken_count,
            "total_doses_skipped": skipped_count,
            "total_doses_scheduled": total_scheduled,
            "clinical_safeguard": cls.SAFEGUARD_MISSED_DOSE_WARNING,
        }

