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

    @classmethod
    def assess_glucose(cls, val: Decimal, reading_type: str = 'FASTING') -> dict:
        """
        Evaluates a blood glucose value against clinical guidelines (ADA / WHO / Bangladesh Clinical Guidelines).
        Returns whether the value is out of normal range, severity level, warning message, and actionable recommendation.
        """
        if val is None:
            return {
                "is_out_of_range": False,
                "severity": "NORMAL",
                "status": "UNKNOWN",
                "warning_title": "",
                "warning_message": "",
                "recommendation": "",
                "is_emergency": False,
            }

        val = Decimal(str(val))
        reading_type = (reading_type or 'FASTING').upper()

        # 1. Critical Hypoglycemia (< 3.9 mmol/L)
        if val < cls.HYPOGLYCEMIA_THRESHOLD_MMOL:
            return {
                "is_out_of_range": True,
                "severity": "CRITICAL",
                "status": "CRITICAL_HYPOGLYCEMIA",
                "warning_title": "Severe Low Blood Sugar (Hypoglycemia Danger)",
                "warning_message": f"Your blood sugar ({val} mmol/L) is critically low (< 3.9 mmol/L). Danger of fainting, severe weakness, or loss of consciousness.",
                "recommendation": "Take 15g fast-acting sugar immediately (1/2 cup fruit juice, 3 candies, or 1 tablespoon honey/sugar). Rest quietly and re-check blood sugar in 15 minutes. Call National Emergency 999 if feeling faint or unresponsive.",
                "is_emergency": True,
            }

        # 2. Critical Hyperglycemia (> 16.0 mmol/L)
        if val > cls.HYPERGLYCEMIA_THRESHOLD_MMOL:
            return {
                "is_out_of_range": True,
                "severity": "CRITICAL",
                "status": "CRITICAL_HYPERGLYCEMIA",
                "warning_title": "Severe High Blood Sugar (Hyperglycemia Crisis)",
                "warning_message": f"Your blood sugar ({val} mmol/L) is dangerously high (> 16.0 mmol/L). High risk of severe dehydration and ketoacidosis/hyperosmolar crisis.",
                "recommendation": "Drink plenty of plain water immediately to prevent severe dehydration, monitor for ketones, and contact your physician or nearest emergency clinic immediately. If vomiting or breathing rapidly, call 999.",
                "is_emergency": True,
            }

        # 3. Mild Low Glucose (< 4.0 mmol/L)
        if val < Decimal('4.0'):
            return {
                "is_out_of_range": True,
                "severity": "WARNING",
                "status": "LOW_GLUCOSE",
                "warning_title": "Low Blood Sugar (< 4.0 mmol/L)",
                "warning_message": f"Your blood sugar ({val} mmol/L) is below the recommended physiological lower limit (4.0 mmol/L).",
                "recommendation": "Have a light balanced snack or meal with complex carbohydrates and protein. Avoid skipping meals and watch for trembling, dizziness, or sweating.",
                "is_emergency": False,
            }

        # 4. Context-Specific Clinical Bands
        if reading_type == 'FASTING':
            if val <= Decimal('5.5'):
                return {
                    "is_out_of_range": False,
                    "severity": "NORMAL",
                    "status": "NORMAL",
                    "warning_title": "Normal Fasting Glucose",
                    "warning_message": f"Fasting blood glucose ({val} mmol/L) is within the optimal healthy target range (4.0 – 5.5 mmol/L).",
                    "recommendation": "Keep up your balanced diet, healthy morning routine, and regular physical activity.",
                    "is_emergency": False,
                }
            elif val <= Decimal('6.9'):
                return {
                    "is_out_of_range": True,
                    "severity": "ELEVATED",
                    "status": "ELEVATED_PREDIABETES",
                    "warning_title": "Elevated Fasting Glucose (Pre-diabetic Range)",
                    "warning_message": f"Fasting reading ({val} mmol/L) is elevated above the standard normal limit (< 5.6 mmol/L).",
                    "recommendation": "Moderate dietary carbohydrates, eliminate sweetened beverages, aim for at least 30 minutes of daily brisk walking, and consult your physician for an HbA1c screening.",
                    "is_emergency": False,
                }
            else: # 7.0 - 16.0
                return {
                    "is_out_of_range": True,
                    "severity": "HIGH",
                    "status": "HIGH_FASTING",
                    "warning_title": "High Fasting Blood Sugar",
                    "warning_message": f"Fasting reading ({val} mmol/L) is significantly above the 7.0 mmol/L diabetic threshold.",
                    "recommendation": "Drink plenty of water, adhere strictly to prescribed diabetes medications or insulin, avoid high-glycemic foods, and consult your healthcare provider to review treatment.",
                    "is_emergency": False,
                }

        elif reading_type == 'POST_MEAL':
            if val < Decimal('7.8'):
                return {
                    "is_out_of_range": False,
                    "severity": "NORMAL",
                    "status": "NORMAL",
                    "warning_title": "Normal Post-Meal Glucose",
                    "warning_message": f"Your 2-hour post-meal glucose ({val} mmol/L) is within the healthy target range (< 7.8 mmol/L).",
                    "recommendation": "Great job! Continue mindful portion sizes and balanced meals.",
                    "is_emergency": False,
                }
            elif val <= Decimal('11.0'):
                return {
                    "is_out_of_range": True,
                    "severity": "ELEVATED",
                    "status": "ELEVATED_POST_MEAL",
                    "warning_title": "Elevated Post-Meal Glucose",
                    "warning_message": f"Your 2-hour post-meal glucose ({val} mmol/L) is above standard target (< 7.8 mmol/L).",
                    "recommendation": "Moderate portion sizes of white rice, roti, and sweets. A light 10–15 minute walk after meals significantly lowers post-meal blood sugar surges.",
                    "is_emergency": False,
                }
            else: # 11.1 - 16.0
                return {
                    "is_out_of_range": True,
                    "severity": "HIGH",
                    "status": "HIGH_POST_MEAL",
                    "warning_title": "High Post-Meal Blood Sugar",
                    "warning_message": f"Your 2-hour post-meal glucose ({val} mmol/L) exceeds 11.1 mmol/L (diabetic post-prandial hyperglycemia).",
                    "recommendation": "Drink water to assist renal clearance, take your diabetes medication as prescribed, log meal components, and review this pattern with your doctor.",
                    "is_emergency": False,
                }

        else: # BEDTIME or RANDOM
            if val <= Decimal('7.7'):
                return {
                    "is_out_of_range": False,
                    "severity": "NORMAL",
                    "status": "NORMAL",
                    "warning_title": "Normal Blood Glucose",
                    "warning_message": f"Your blood glucose ({val} mmol/L) is within expected normal reference parameters (< 7.8 mmol/L).",
                    "recommendation": "Continue following your healthy lifestyle and balanced diet.",
                    "is_emergency": False,
                }
            elif val <= Decimal('11.0'):
                return {
                    "is_out_of_range": True,
                    "severity": "ELEVATED",
                    "status": "ELEVATED_RANDOM",
                    "warning_title": "Elevated Blood Glucose",
                    "warning_message": f"Blood glucose ({val} mmol/L) is higher than standard normal daytime targets.",
                    "recommendation": "Stay well hydrated, avoid sugary snacks, and maintain regular meal schedules.",
                    "is_emergency": False,
                }
            else: # 11.1 - 16.0
                return {
                    "is_out_of_range": True,
                    "severity": "HIGH",
                    "status": "HIGH_RANDOM",
                    "warning_title": "High Blood Glucose",
                    "warning_message": f"Blood glucose ({val} mmol/L) is elevated in the diabetic hyperglycemia range (>= 11.1 mmol/L).",
                    "recommendation": "Drink plenty of water, adhere to your prescribed medical regimen, and schedule a follow-up with your doctor if readings stay elevated.",
                    "is_emergency": False,
                }

    @classmethod
    def assess_blood_pressure(cls, sys: int, dia: int, pulse: Optional[int] = None) -> dict:
        """
        Evaluates blood pressure readings against standardized AHA and Bangladesh National Guidelines.
        Returns staging, out-of-range status, severity, warning message, and actionable recommendation.
        """
        if sys is None or dia is None:
            return {
                "is_out_of_range": False,
                "severity": "NORMAL",
                "status": "UNKNOWN",
                "warning_title": "",
                "warning_message": "",
                "recommendation": "",
                "is_emergency": False,
            }

        pulse_note = ""
        pulse_warning = ""
        if pulse:
            if pulse < 50:
                pulse_note = f", Pulse: {pulse} bpm (Bradycardia)"
                pulse_warning = f" Pulse of {pulse} bpm indicates bradycardia (slow heart rate)."
            elif pulse > 100:
                pulse_note = f", Pulse: {pulse} bpm (Tachycardia)"
                pulse_warning = f" Pulse of {pulse} bpm indicates tachycardia (elevated resting heart rate)."

        # 1. Hypertensive Crisis (Systolic > 180 OR Diastolic > 120)
        if sys > cls.CRISIS_SYSTOLIC_THRESHOLD or dia > cls.CRISIS_DIASTOLIC_THRESHOLD:
            return {
                "is_out_of_range": True,
                "severity": "CRITICAL",
                "status": "HYPERTENSIVE_CRISIS",
                "warning_title": "Hypertensive Crisis Alert (> 180 / 120 mmHg)",
                "warning_message": f"Critical blood pressure detected: {sys}/{dia} mmHg{pulse_note}. Extremely high vascular pressure.{pulse_warning}",
                "recommendation": "Rest calmly in a seated position for 5 minutes and repeat measurement. If reading remains above 180/120 mmHg or you experience severe headache, blurred vision, chest discomfort, or shortness of breath, call National Emergency 999 or proceed immediately to the nearest hospital emergency room.",
                "is_emergency": True,
            }

        # 2. Stage 2 Hypertension (Systolic >= 140 OR Diastolic >= 90)
        if sys >= 140 or dia >= 90:
            return {
                "is_out_of_range": True,
                "severity": "HIGH",
                "status": "STAGE_2_HYPERTENSION",
                "warning_title": "Stage 2 Hypertension (>= 140/90 mmHg)",
                "warning_message": f"Your blood pressure ({sys}/{dia} mmHg{pulse_note}) is classified as Stage 2 Hypertension.{pulse_warning}",
                "recommendation": "Rest calmly for 15 minutes and retake reading. Take any prescribed antihypertensive medication as directed. Avoid table salt, caffeine, and smoking. Consult your physician promptly for clinical management.",
                "is_emergency": False,
            }

        # 3. Hypotension / Low BP (Systolic < 90 OR Diastolic < 60)
        if sys < 90 or dia < 60:
            return {
                "is_out_of_range": True,
                "severity": "WARNING",
                "status": "HYPOTENSION",
                "warning_title": "Low Blood Pressure / Hypotension (< 90/60 mmHg)",
                "warning_message": f"Your blood pressure ({sys}/{dia} mmHg{pulse_note}) is lower than standard physiological limits (90/60 mmHg).{pulse_warning}",
                "recommendation": "Sit or lie down with legs slightly elevated. Drink fluids or oral rehydration saline (ORS). Avoid sudden standing. If experiencing dizziness, cold clammy skin, or lightheadedness, rest and contact your healthcare provider.",
                "is_emergency": False,
            }

        # 4. Normal Blood Pressure (Systolic <= 120 AND Diastolic <= 80, including standard 120/80 mmHg)
        if sys <= 120 and dia <= 80:
            return {
                "is_out_of_range": False,
                "severity": "NORMAL",
                "status": "NORMAL",
                "warning_title": "Normal Blood Pressure (120/80 mmHg Target)",
                "warning_message": f"Optimal blood pressure ({sys}/{dia} mmHg{pulse_note}). Reading is within healthy target guidelines.{pulse_warning}",
                "recommendation": "Great job! Maintain your balanced low-salt diet, regular physical exercise, and restorative sleep habits.",
                "is_emergency": False,
            }

        # 5. Elevated BP (Systolic 121-129 AND Diastolic <= 80)
        if (120 < sys <= 129) and dia <= 80:
            return {
                "is_out_of_range": True,
                "severity": "ELEVATED",
                "status": "ELEVATED",
                "warning_title": "Elevated Blood Pressure (121-129 / <=80 mmHg)",
                "warning_message": f"Systolic pressure ({sys} mmHg{pulse_note}) is slightly elevated above 120 mmHg.{pulse_warning}",
                "recommendation": "Adopt heart-healthy nutrition (DASH diet rich in vegetables, fruits, and potassium), limit sodium intake, stay active, and monitor your BP weekly.",
                "is_emergency": False,
            }

        # 6. Stage 1 Hypertension (Systolic 130-139 OR Diastolic 81-89)
        if (130 <= sys <= 139) or (80 < dia <= 89):
            return {
                "is_out_of_range": True,
                "severity": "WARNING",
                "status": "STAGE_1_HYPERTENSION",
                "warning_title": "Stage 1 Hypertension (130-139 / 81-89 mmHg)",
                "warning_message": f"Your blood pressure ({sys}/{dia} mmHg{pulse_note}) is in Stage 1 Hypertension.{pulse_warning}",
                "recommendation": "Focus on lifestyle modifications: reduce dietary salt/sodium, engage in 30 minutes of daily aerobic exercise, manage stress, and maintain a daily morning/evening BP log to review with your doctor.",
                "is_emergency": False,
            }

        # Default fallback
        return {
            "is_out_of_range": False,
            "severity": "NORMAL",
            "status": "NORMAL",
            "warning_title": "Normal Blood Pressure",
            "warning_message": f"Blood pressure ({sys}/{dia} mmHg{pulse_note}) recorded.",
            "recommendation": "Continue healthy lifestyle habits.",
            "is_emergency": False,
        }
