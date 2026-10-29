from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Hard physiological limits (reject typos outside human survivability / measurement plausibility)
MIN_GLUCOSE_MMOL = Decimal('0.5')
MAX_GLUCOSE_MMOL = Decimal('60.0')

MIN_SYSTOLIC = 40
MAX_SYSTOLIC = 300

MIN_DIASTOLIC = 30
MAX_DIASTOLIC = 200

MIN_PULSE_BPM = 30
MAX_PULSE_BPM = 250

MIN_WEIGHT_KG = Decimal('1.0')
MAX_WEIGHT_KG = Decimal('400.0')

def validate_glucose_value(value):
    if value < MIN_GLUCOSE_MMOL or value > MAX_GLUCOSE_MMOL:
        raise ValidationError(
            _(f"Plausible blood glucose range is {MIN_GLUCOSE_MMOL} to {MAX_GLUCOSE_MMOL} mmol/L. "
              f"Value {value} is out of physiological bounds.")
        )

def validate_systolic_value(value):
    if value < MIN_SYSTOLIC or value > MAX_SYSTOLIC:
        raise ValidationError(
            _(f"Plausible systolic blood pressure is {MIN_SYSTOLIC} to {MAX_SYSTOLIC} mmHg.")
        )

def validate_diastolic_value(value):
    if value < MIN_DIASTOLIC or value > MAX_DIASTOLIC:
        raise ValidationError(
            _(f"Plausible diastolic blood pressure is {MIN_DIASTOLIC} to {MAX_DIASTOLIC} mmHg.")
        )

def validate_pulse_value(value):
    if value is not None and (value < MIN_PULSE_BPM or value > MAX_PULSE_BPM):
        raise ValidationError(
            _(f"Plausible pulse rate is {MIN_PULSE_BPM} to {MAX_PULSE_BPM} bpm.")
        )

def validate_weight_value(value):
    if value < MIN_WEIGHT_KG or value > MAX_WEIGHT_KG:
        raise ValidationError(
            _(f"Plausible weight is {MIN_WEIGHT_KG} to {MAX_WEIGHT_KG} kg.")
        )

