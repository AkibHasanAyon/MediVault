from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel
from .validators import (
    validate_glucose_value,
    validate_systolic_value,
    validate_diastolic_value,
    validate_pulse_value,
    validate_weight_value,
)

class BloodGlucoseLog(TimeStampedUUIDModel):
    class ReadingType(models.TextChoices):
        FASTING = 'FASTING', _('Fasting (Before Breakfast)')
        POST_MEAL = 'POST_MEAL', _('2 Hours Post Meal')
        BEDTIME = 'BEDTIME', _('Bedtime')
        RANDOM = 'RANDOM', _('Random / Any Time')

    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='glucose_logs')
    family_member = models.ForeignKey('patients.FamilyMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='glucose_logs')
    glucose_value_mmol = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        validators=[validate_glucose_value],
        help_text=_("Glucose value in mmol/L")
    )
    reading_type = models.CharField(max_length=20, choices=ReadingType.choices, default=ReadingType.FASTING)
    recorded_at = models.DateTimeField(db_index=True)
    notes = models.TextField(blank=True)
    is_danger = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = _('Blood Glucose Log')
        verbose_name_plural = _('Blood Glucose Logs')
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['patient', 'recorded_at']),
        ]

    def __str__(self):
        target = self.family_member.full_name if self.family_member else self.patient.user.full_name
        return f"{target} - {self.glucose_value_mmol} mmol/L ({self.reading_type})"


class BloodPressureLog(TimeStampedUUIDModel):
    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='bp_logs')
    family_member = models.ForeignKey('patients.FamilyMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='bp_logs')
    systolic_mmHg = models.PositiveSmallIntegerField(
        validators=[validate_systolic_value],
        help_text=_("Systolic (top number, mmHg)")
    )
    diastolic_mmHg = models.PositiveSmallIntegerField(
        validators=[validate_diastolic_value],
        help_text=_("Diastolic (bottom number, mmHg)")
    )
    pulse_bpm = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[validate_pulse_value],
        help_text=_("Heart rate / Pulse in beats per minute")
    )
    recorded_at = models.DateTimeField(db_index=True)
    is_crisis = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = _('Blood Pressure Log')
        verbose_name_plural = _('Blood Pressure Logs')
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['patient', 'recorded_at']),
        ]

    @property
    def is_hypertensive_crisis(self) -> bool:
        """Standardized American Heart Association / Bangladesh Clinical Protocol: Systolic > 180 OR Diastolic > 120."""
        return self.systolic_mmHg > 180 or self.diastolic_mmHg > 120

    def __str__(self):
        target = self.family_member.full_name if self.family_member else self.patient.user.full_name
        return f"{target} - {self.systolic_mmHg}/{self.diastolic_mmHg} mmHg"


class WeightLog(TimeStampedUUIDModel):
    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='weight_logs')
    family_member = models.ForeignKey('patients.FamilyMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='weight_logs')
    weight_kg = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[validate_weight_value],
        help_text=_("Weight in kilograms")
    )
    calculated_bmi = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    recorded_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = _('Weight Log')
        verbose_name_plural = _('Weight Logs')
        ordering = ['-recorded_at']

    def __str__(self):
        return f"{self.patient.user.full_name} - {self.weight_kg} kg"


class SymptomNote(TimeStampedUUIDModel):
    class Severity(models.TextChoices):
        MILD = 'MILD', _('Mild')
        MODERATE = 'MODERATE', _('Moderate')
        SEVERE = 'SEVERE', _('Severe')

    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='symptom_notes')
    family_member = models.ForeignKey('patients.FamilyMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='symptom_notes')
    symptom_tags = models.CharField(max_length=255, help_text=_("Comma-separated symptom tags e.g. Dizziness, Headache"))
    severity = models.CharField(max_length=15, choices=Severity.choices, default=Severity.MILD)
    notes = models.TextField(blank=True)
    onset_time = models.DateTimeField(null=True, blank=True)
    recorded_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = _('Symptom Note')
        verbose_name_plural = _('Symptom Notes')
        ordering = ['-recorded_at']


class DangerAlert(TimeStampedUUIDModel):
    class AlertType(models.TextChoices):
        HYPOGLYCEMIA = 'HYPOGLYCEMIA', _('Hypoglycemia (<3.9 mmol/L)')
        HYPERGLYCEMIA = 'HYPERGLYCEMIA', _('Hyperglycemia (>16.0 mmol/L)')
        HYPERTENSIVE_CRISIS = 'HYPERTENSIVE_CRISIS', _('Hypertensive Crisis (>180 Systolic OR >120 Diastolic mmHg)')

    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='danger_alerts')
    family_member = models.ForeignKey('patients.FamilyMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='danger_alerts')
    alert_type = models.CharField(max_length=30, choices=AlertType.choices, db_index=True)
    trigger_value = models.CharField(max_length=50)
    instruction_text = models.TextField()
    is_acknowledged = models.BooleanField(default=False)
    notification_dispatched = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Danger Alert')
        verbose_name_plural = _('Danger Alerts')
        ordering = ['-created_at']

    def __str__(self):
        return f"🚨 {self.alert_type} ({self.trigger_value}) for {self.patient.user.full_name}"

