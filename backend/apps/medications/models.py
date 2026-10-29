from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel

class Medication(TimeStampedUUIDModel):
    class Provenance(models.TextChoices):
        CLINICIAN_AUTHORED = 'CLINICIAN_AUTHORED', _('Direct from Doctor Prescription')
        OCR_EXTRACTED = 'OCR_EXTRACTED', _('Extracted from Uploaded Prescription')
        MANUAL_ENTRY = 'MANUAL_ENTRY', _('Manually Added by Patient')

    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='medications')
    family_member = models.ForeignKey('patients.FamilyMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='medications')
    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255, blank=True)
    strength = models.CharField(max_length=50)
    dosage_pattern = models.CharField(max_length=50, help_text=_("e.g. 1+0+1"))
    is_active = models.BooleanField(default=True, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    refill_remaining_doses = models.PositiveSmallIntegerField(default=30)
    source_prescription = models.ForeignKey('prescriptions.Prescription', on_delete=models.SET_NULL, null=True, blank=True, related_name='active_medications')
    provenance = models.CharField(max_length=30, choices=Provenance.choices, default=Provenance.MANUAL_ENTRY)

    class Meta:
        verbose_name = _('Patient Active Medication')
        verbose_name_plural = _('Patient Active Medications')
        ordering = ['name']

    def __str__(self):
        target = self.family_member.full_name if self.family_member else self.patient.user.full_name
        return f"{self.name} {self.strength} ({self.dosage_pattern}) - {target}"


class MedicationReminder(TimeStampedUUIDModel):
    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='reminders')
    reminder_time = models.TimeField(help_text=_("Scheduled alarm time e.g. 08:00:00"))
    label = models.CharField(max_length=50, default='Morning Dose')
    is_enabled = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = _('Medication Reminder Schedule')
        verbose_name_plural = _('Medication Reminder Schedules')
        ordering = ['reminder_time']

    def __str__(self):
        return f"{self.medication.name} at {self.reminder_time.strftime('%I:%M %p')}"


class MedicationAdherence(TimeStampedUUIDModel):
    class Action(models.TextChoices):
        TAKEN = 'TAKEN', _('Taken')
        SKIPPED = 'SKIPPED', _('Skipped')
        SNOOZED = 'SNOOZED', _('Snoozed')

    medication = models.ForeignKey(Medication, on_delete=models.CASCADE, related_name='adherence_logs')
    reminder = models.ForeignKey(MedicationReminder, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=15, choices=Action.choices, default=Action.TAKEN, db_index=True)
    scheduled_time = models.DateTimeField(db_index=True)
    recorded_time = models.DateTimeField(auto_now_add=True)
    skip_reason = models.CharField(max_length=255, blank=True, help_text=_("e.g. Side effects, Ran out of pills, Forgot"))

    class Meta:
        verbose_name = _('Medication Adherence Entry')
        verbose_name_plural = _('Medication Adherence Entries')
        ordering = ['-scheduled_time']

    def __str__(self):
        return f"{self.medication.name} - {self.action} at {self.scheduled_time.strftime('%Y-%m-%d %H:%M')}"

