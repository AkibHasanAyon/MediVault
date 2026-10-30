import logging
from decimal import Decimal
from typing import Optional

from .models import BloodGlucoseLog, BloodPressureLog, DangerAlert

logger = logging.getLogger('medivault.alerts')

class DangerAlertEngine:
    """
    Algorithmic Clinical Rule Engine for MediVault.
    Evaluates vitals against validated physiological thresholds and creates
    unambiguous, actionable emergency alerts without diagnostic speculation.
    """

    HYPOGLYCEMIA_THRESHOLD_MMOL = Decimal('3.9')
    HYPERGLYCEMIA_THRESHOLD_MMOL = Decimal('16.0')
    CRISIS_SYSTOLIC_THRESHOLD = 180
    CRISIS_DIASTOLIC_THRESHOLD = 120

    @classmethod
    def evaluate_glucose(cls, log: BloodGlucoseLog) -> Optional[DangerAlert]:
        val = log.glucose_value_mmol
        alert_type = None
        instruction = ""

        if val < cls.HYPOGLYCEMIA_THRESHOLD_MMOL:
            alert_type = DangerAlert.AlertType.HYPOGLYCEMIA
            instruction = (
                "Take 15g fast-acting sugar immediately (1/2 cup fruit juice or 3 candies). "
                "Rest and re-check blood glucose in 15 minutes. "
                "Call National Emergency 999 if feeling faint or unresponsive."
            )
        elif val > cls.HYPERGLYCEMIA_THRESHOLD_MMOL:
            alert_type = DangerAlert.AlertType.HYPERGLYCEMIA
            instruction = (
                "Critical high blood glucose level (> 16.0 mmol/L). "
                "Drink plenty of water to prevent severe dehydration, monitor for ketones, "
                "and contact your physician immediately. If vomiting, call 999."
            )

        if alert_type:
            alert = DangerAlert.objects.create(
                patient=log.patient,
                family_member=log.family_member,
                alert_type=alert_type,
                trigger_value=f"{val} mmol/L",
                instruction_text=instruction
            )
            logger.warning("🚨 Triggered %s danger alert for patient %s (Value: %s)", alert_type, log.patient.user.phone_number, val)
            return alert

        return None

    @classmethod
    def evaluate_blood_pressure(cls, log: BloodPressureLog) -> Optional[DangerAlert]:
        """
        Evaluates Hypertensive Crisis using standardized AHA / Bangladesh Clinical Protocol.
        Standard OR logic: Systolic > 180 OR Diastolic > 120 triggers crisis.
        """
        sys = log.systolic_mmHg
        dia = log.diastolic_mmHg

        if sys > cls.CRISIS_SYSTOLIC_THRESHOLD or dia > cls.CRISIS_DIASTOLIC_THRESHOLD:
            instruction = (
                "Hypertensive Crisis detected! Rest calmly for 5 minutes and repeat measurement. "
                "If reading remains above 180/120 or you experience severe headache, blurred vision, "
                "chest discomfort or breathlessness, call National Emergency 999 or proceed to nearest hospital emergency room immediately."
            )
            alert = DangerAlert.objects.create(
                patient=log.patient,
                family_member=log.family_member,
                alert_type=DangerAlert.AlertType.HYPERTENSIVE_CRISIS,
                trigger_value=f"{sys}/{dia} mmHg",
                instruction_text=instruction
            )
            logger.warning(
                "🚨 Triggered HYPERTENSIVE_CRISIS alert for patient %s (Reading: %s/%s mmHg)",
                log.patient.user.phone_number, sys, dia
            )
            return alert

        return None

