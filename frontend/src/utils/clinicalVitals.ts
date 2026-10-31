export interface ClinicalAssessment {
  isOutOfRange: boolean;
  severity: 'NORMAL' | 'ELEVATED' | 'WARNING' | 'HIGH' | 'CRITICAL';
  status: string;
  warningTitle: string;
  warningMessage: string;
  recommendation: string;
  isEmergency?: boolean;
}

/**
 * Assesses blood glucose reading against ADA / WHO / Bangladesh Clinical Guidelines
 */
export function assessGlucose(
  valueMmol: number | null | undefined,
  context: 'FASTING' | 'POST_MEAL' | 'BEDTIME' | 'RANDOM' | string = 'FASTING'
): ClinicalAssessment | null {
  if (valueMmol === null || valueMmol === undefined || isNaN(valueMmol) || valueMmol <= 0) {
    return null;
  }

  const val = Number(valueMmol.toFixed(1));
  const ctx = (context || 'FASTING').toUpperCase();

  // 1. Critical Hypoglycemia (< 3.9 mmol/L)
  if (val < 3.9) {
    return {
      isOutOfRange: true,
      severity: 'CRITICAL',
      status: 'CRITICAL_HYPOGLYCEMIA',
      warningTitle: 'Severe Low Blood Sugar (Hypoglycemia Danger)',
      warningMessage: `Your blood sugar (${val} mmol/L) is critically low (< 3.9 mmol/L). Immediate action is required to prevent fainting or loss of consciousness.`,
      recommendation:
        'Take 15g of fast-acting sugar immediately (1/2 cup fruit juice, 3 candies, or 1 tablespoon honey/sugar). Rest and re-check blood glucose in 15 minutes. Call National Emergency 999 if feeling faint or unresponsive.',
      isEmergency: true,
    };
  }

  // 2. Critical Hyperglycemia (> 16.0 mmol/L)
  if (val > 16.0) {
    return {
      isOutOfRange: true,
      severity: 'CRITICAL',
      status: 'CRITICAL_HYPERGLYCEMIA',
      warningTitle: 'Severe High Blood Sugar (Hyperglycemia Crisis)',
      warningMessage: `Your blood sugar (${val} mmol/L) is critically elevated (> 16.0 mmol/L). High risk of severe dehydration and hyperosmolar/ketoacidosis crisis.`,
      recommendation:
        'Drink plenty of plain water immediately to prevent severe dehydration, monitor for ketones, and contact your physician or visit the nearest emergency room immediately. If vomiting or breathing heavily, call 999.',
      isEmergency: true,
    };
  }

  // 3. Mild Low Glucose (< 4.0 mmol/L)
  if (val < 4.0) {
    return {
      isOutOfRange: true,
      severity: 'WARNING',
      status: 'LOW_GLUCOSE',
      warningTitle: 'Low Blood Sugar (< 4.0 mmol/L)',
      warningMessage: `Your blood sugar (${val} mmol/L) is below the recommended physiological lower limit (4.0 mmol/L).`,
      recommendation:
        'Have a light balanced snack or meal with complex carbohydrates and protein. Avoid skipping meals and monitor for trembling, dizziness, or sweating.',
      isEmergency: false,
    };
  }

  // 4. Context specific
  if (ctx === 'FASTING') {
    if (val <= 5.5) {
      return {
        isOutOfRange: false,
        severity: 'NORMAL',
        status: 'NORMAL',
        warningTitle: 'Normal Fasting Glucose (4.0 – 5.5 mmol/L)',
        warningMessage: `Fasting blood glucose (${val} mmol/L) is within the optimal healthy target range.`,
        recommendation: 'Keep up your balanced nutrition, healthy morning routine, and regular physical exercise.',
        isEmergency: false,
      };
    } else if (val <= 6.9) {
      return {
        isOutOfRange: true,
        severity: 'ELEVATED',
        status: 'ELEVATED_PREDIABETES',
        warningTitle: 'Elevated Fasting Glucose (Pre-diabetic Range: 5.6 – 6.9 mmol/L)',
        warningMessage: `Fasting reading (${val} mmol/L) is elevated above the standard normal limit (< 5.6 mmol/L).`,
        recommendation:
          'Moderate dietary carbohydrates, eliminate sweetened drinks, aim for at least 30 minutes of daily brisk walking, and consult your physician for an HbA1c test.',
        isEmergency: false,
      };
    } else {
      return {
        isOutOfRange: true,
        severity: 'HIGH',
        status: 'HIGH_FASTING',
        warningTitle: 'High Fasting Blood Sugar (≥ 7.0 mmol/L)',
        warningMessage: `Fasting reading (${val} mmol/L) is above the 7.0 mmol/L diabetic threshold.`,
        recommendation:
          'Drink plenty of water, adhere strictly to prescribed diabetes medications or insulin, avoid high-glycemic foods, and consult your healthcare provider to review treatment.',
        isEmergency: false,
      };
    }
  } else if (ctx === 'POST_MEAL') {
    if (val < 7.8) {
      return {
        isOutOfRange: false,
        severity: 'NORMAL',
        status: 'NORMAL',
        warningTitle: 'Normal Post-Meal Glucose (< 7.8 mmol/L)',
        warningMessage: `Your 2-hour post-meal glucose (${val} mmol/L) is within the healthy target range.`,
        recommendation: 'Great job! Continue mindful portion sizes and balanced meals.',
        isEmergency: false,
      };
    } else if (val <= 11.0) {
      return {
        isOutOfRange: true,
        severity: 'ELEVATED',
        status: 'ELEVATED_POST_MEAL',
        warningTitle: 'Elevated Post-Meal Glucose (7.8 – 11.0 mmol/L)',
        warningMessage: `Your 2-hour post-meal glucose (${val} mmol/L) is above standard target (< 7.8 mmol/L).`,
        recommendation:
          'Moderate portion sizes of white rice, roti, and sweets. A light 10–15 minute walk after meals significantly lowers post-meal blood sugar surges.',
        isEmergency: false,
      };
    } else {
      return {
        isOutOfRange: true,
        severity: 'HIGH',
        status: 'HIGH_POST_MEAL',
        warningTitle: 'High Post-Meal Blood Sugar (≥ 11.1 mmol/L)',
        warningMessage: `Your 2-hour post-meal glucose (${val} mmol/L) exceeds 11.1 mmol/L (diabetic post-prandial hyperglycemia).`,
        recommendation:
          'Drink water to assist renal clearance, take your diabetes medication as prescribed, log meal components, and review this pattern with your doctor.',
        isEmergency: false,
      };
    }
  } else {
    // Bedtime or Random
    if (val <= 7.7) {
      return {
        isOutOfRange: false,
        severity: 'NORMAL',
        status: 'NORMAL',
        warningTitle: 'Normal Blood Glucose (< 7.8 mmol/L)',
        warningMessage: `Your blood glucose (${val} mmol/L) is within expected normal reference parameters.`,
        recommendation: 'Continue following your healthy lifestyle and balanced diet.',
        isEmergency: false,
      };
    } else if (val <= 11.0) {
      return {
        isOutOfRange: true,
        severity: 'ELEVATED',
        status: 'ELEVATED_RANDOM',
        warningTitle: 'Elevated Blood Glucose (7.8 – 11.0 mmol/L)',
        warningMessage: `Blood glucose (${val} mmol/L) is higher than standard normal daytime targets.`,
        recommendation: 'Stay well hydrated, avoid sugary snacks, and maintain regular meal schedules.',
        isEmergency: false,
      };
    } else {
      return {
        isOutOfRange: true,
        severity: 'HIGH',
        status: 'HIGH_RANDOM',
        warningTitle: 'High Blood Glucose (≥ 11.1 mmol/L)',
        warningMessage: `Blood glucose (${val} mmol/L) is elevated in the diabetic hyperglycemia range (≥ 11.1 mmol/L).`,
        recommendation:
          'Drink plenty of water, adhere to your prescribed medical regimen, and schedule a follow-up with your doctor if readings stay elevated.',
        isEmergency: false,
      };
    }
  }
}

/**
 * Assesses blood pressure reading against AHA and Bangladesh National Guidelines
 */
export function assessBloodPressure(
  systolic: number | null | undefined,
  diastolic: number | null | undefined,
  pulse?: number | null | undefined
): ClinicalAssessment | null {
  if (
    systolic === null ||
    systolic === undefined ||
    diastolic === null ||
    diastolic === undefined ||
    isNaN(systolic) ||
    isNaN(diastolic) ||
    systolic <= 0 ||
    diastolic <= 0
  ) {
    return null;
  }

  const sys = Math.round(systolic);
  const dia = Math.round(diastolic);
  const pls = pulse && !isNaN(pulse) ? Math.round(pulse) : undefined;

  let pulseNote = '';
  let pulseWarning = '';
  if (pls) {
    if (pls < 50) {
      pulseNote = `, Pulse: ${pls} bpm (Bradycardia)`;
      pulseWarning = ` Pulse of ${pls} bpm indicates bradycardia (slow heart rate).`;
    } else if (pls > 100) {
      pulseNote = `, Pulse: ${pls} bpm (Tachycardia)`;
      pulseWarning = ` Pulse of ${pls} bpm indicates tachycardia (elevated resting heart rate).`;
    }
  }

  // 1. Hypertensive Crisis (Systolic > 180 OR Diastolic > 120)
  if (sys > 180 || dia > 120) {
    return {
      isOutOfRange: true,
      severity: 'CRITICAL',
      status: 'HYPERTENSIVE_CRISIS',
      warningTitle: 'Hypertensive Crisis Alert (> 180 / 120 mmHg)',
      warningMessage: `Critical blood pressure detected: ${sys}/${dia} mmHg${pulseNote}. Extremely high vascular pressure.${pulseWarning}`,
      recommendation:
        'Rest calmly in a seated position for 5 minutes and repeat measurement. If reading remains above 180/120 mmHg or you experience severe headache, blurred vision, chest discomfort, or shortness of breath, call National Emergency 999 or proceed immediately to the nearest hospital emergency room.',
      isEmergency: true,
    };
  }

  // 2. Stage 2 Hypertension (Systolic >= 140 OR Diastolic >= 90)
  if (sys >= 140 || dia >= 90) {
    return {
      isOutOfRange: true,
      severity: 'HIGH',
      status: 'STAGE_2_HYPERTENSION',
      warningTitle: 'Stage 2 Hypertension (≥ 140/90 mmHg)',
      warningMessage: `Your blood pressure (${sys}/${dia} mmHg${pulseNote}) is classified as Stage 2 Hypertension.${pulseWarning}`,
      recommendation:
        'Rest calmly for 15 minutes and retake reading. Take any prescribed antihypertensive medication as directed. Avoid table salt, caffeine, and smoking. Consult your physician promptly for clinical management.',
      isEmergency: false,
    };
  }

  // 3. Hypotension / Low BP (Systolic < 90 OR Diastolic < 60)
  if (sys < 90 || dia < 60) {
    return {
      isOutOfRange: true,
      severity: 'WARNING',
      status: 'HYPOTENSION',
      warningTitle: 'Low Blood Pressure / Hypotension (< 90/60 mmHg)',
      warningMessage: `Your blood pressure (${sys}/${dia} mmHg${pulseNote}) is lower than standard physiological limits (90/60 mmHg).${pulseWarning}`,
      recommendation:
        'Sit or lie down with legs slightly elevated. Drink fluids or oral rehydration saline (ORS). Avoid sudden standing. If experiencing dizziness, cold clammy skin, or lightheadedness, rest and contact your healthcare provider.',
      isEmergency: false,
    };
  }

  // 4. Normal Blood Pressure (Systolic <= 120 AND Diastolic <= 80, including standard 120/80 mmHg)
  if (sys <= 120 && dia <= 80) {
    return {
      isOutOfRange: false,
      severity: 'NORMAL',
      status: 'NORMAL',
      warningTitle: 'Normal Blood Pressure (120/80 mmHg Target)',
      warningMessage: `Optimal blood pressure (${sys}/${dia} mmHg${pulseNote}). Reading is within healthy target guidelines.${pulseWarning}`,
      recommendation:
        'Great job! Maintain your balanced low-salt diet, regular physical exercise, and restorative sleep habits.',
      isEmergency: false,
    };
  }

  // 5. Elevated BP (Systolic 121-129 AND Diastolic <= 80)
  if (sys > 120 && sys <= 129 && dia <= 80) {
    return {
      isOutOfRange: true,
      severity: 'ELEVATED',
      status: 'ELEVATED',
      warningTitle: 'Elevated Blood Pressure (121-129 / ≤80 mmHg)',
      warningMessage: `Systolic pressure (${sys} mmHg${pulseNote}) is slightly elevated above 120 mmHg.${pulseWarning}`,
      recommendation:
        'Adopt heart-healthy nutrition (DASH diet rich in vegetables, fruits, and potassium), limit sodium intake, stay active, and monitor your BP weekly.',
      isEmergency: false,
    };
  }

  // 6. Stage 1 Hypertension (Systolic 130-139 OR Diastolic 81-89)
  if ((sys >= 130 && sys <= 139) || (dia > 80 && dia <= 89)) {
    return {
      isOutOfRange: true,
      severity: 'WARNING',
      status: 'STAGE_1_HYPERTENSION',
      warningTitle: 'Stage 1 Hypertension (130-139 / 81-89 mmHg)',
      warningMessage: `Your blood pressure (${sys}/${dia} mmHg${pulseNote}) is in Stage 1 Hypertension.${pulseWarning}`,
      recommendation:
        'Focus on lifestyle modifications: reduce dietary salt/sodium, engage in 30 minutes of daily aerobic exercise, manage stress, and maintain a daily morning/evening BP log to review with your doctor.',
      isEmergency: false,
    };
  }

  // Default fallback
  return {
    isOutOfRange: false,
    severity: 'NORMAL',
    status: 'NORMAL',
    warningTitle: 'Normal Blood Pressure',
    warningMessage: `Blood pressure (${sys}/${dia} mmHg${pulseNote}) recorded.`,
    recommendation: 'Continue maintaining healthy lifestyle habits.',
    isEmergency: false,
  };
}

