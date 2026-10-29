from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel

class Appointment(TimeStampedUUIDModel):
    class Status(models.TextChoices):
        BOOKED = 'BOOKED', _('Pre-Booked')
        ARRIVED = 'ARRIVED', _('Arrived at Chamber')
        IN_CONSULTATION = 'IN_CONSULTATION', _('In Consultation')
        COMPLETED = 'COMPLETED', _('Completed')
        CANCELLED = 'CANCELLED', _('Cancelled')
        NO_SHOW = 'NO_SHOW', _('No Show')

    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='appointments')
    family_member = models.ForeignKey('patients.FamilyMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE, related_name='appointments')
    clinic = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE, related_name='appointments')
    scheduled_date = models.DateField(db_index=True)
    slot_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.BOOKED, db_index=True)

    class Meta:
        verbose_name = _('Appointment')
        verbose_name_plural = _('Appointments')
        ordering = ['scheduled_date', 'slot_time']

    def __str__(self):
        target = self.family_member.full_name if self.family_member else self.patient.user.full_name
        return f"{target} with Dr. {self.doctor.user.full_name} on {self.scheduled_date}"


class QueueEntry(TimeStampedUUIDModel):
    class State(models.TextChoices):
        WAITING = 'WAITING', _('Waiting in Lobby')
        CALLED_IN = 'CALLED_IN', _('Called to Chamber')
        IN_CHAMBER = 'IN_CHAMBER', _('With Doctor')
        DONE = 'DONE', _('Completed')
        SKIPPED = 'SKIPPED', _('Skipped / Temporary Absence')
        NO_SHOW = 'NO_SHOW', _('No Show')

    clinic = models.ForeignKey('clinics.Clinic', on_delete=models.CASCADE, related_name='queue_entries')
    doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE, related_name='queue_entries')
    appointment = models.OneToOneField(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='queue_entry')
    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='queue_entries')
    family_member = models.ForeignKey('patients.FamilyMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='queue_entries')
    
    token_number = models.PositiveSmallIntegerField(help_text=_("Chamber serial integer for today"))
    token_display = models.CharField(max_length=20, blank=True, help_text=_("Formatted serial e.g. A-012"))
    queue_date = models.DateField(db_index=True)
    state = models.CharField(max_length=20, choices=State.choices, default=State.WAITING, db_index=True)
    estimated_wait_minutes = models.PositiveSmallIntegerField(default=15)
    called_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _('Chamber Queue Entry')
        verbose_name_plural = _('Chamber Queue Entries')
        unique_together = ('clinic', 'doctor', 'queue_date', 'token_number')
        ordering = ['queue_date', 'token_number']

    def save(self, *args, **kwargs):
        if not self.token_display:
            self.token_display = f"A-{self.token_number:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.token_display} ({self.state}) - Dr. {self.doctor.user.full_name}"


class PreAppointmentSummary(TimeStampedUUIDModel):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='pre_summary')
    primary_concern = models.TextField(help_text=_("What is the primary concern for this visit?"))
    reported_symptoms = models.TextField(help_text=_("Recent symptoms experienced"))
    medication_side_effects = models.TextField(blank=True, help_text=_("Any medication side effects noticed"))
    ai_synthesized_brief = models.TextField(blank=True, help_text=_("1-page synthesized brief for consulting doctor"))

    class Meta:
        verbose_name = _('Pre-Appointment Intake Summary')
        verbose_name_plural = _('Pre-Appointment Intake Summaries')


class FollowUpReminder(TimeStampedUUIDModel):
    class Milestone(models.TextChoices):
        TWO_MONTHS_BEFORE = 'TWO_MONTHS_BEFORE', _('2.5 Months / Early Notice')
        ONE_WEEK_BEFORE = 'ONE_WEEK_BEFORE', _('1 Week Before')
        DUE_DATE = 'DUE_DATE', _('Due Date')

    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='follow_up_reminders')
    doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE, related_name='patient_follow_ups')
    prescription = models.ForeignKey('prescriptions.Prescription', on_delete=models.SET_NULL, null=True, blank=True)
    due_date = models.DateField(db_index=True)
    milestone_stage = models.CharField(max_length=25, choices=Milestone.choices, default=Milestone.DUE_DATE)
    is_dispatched = models.BooleanField(default=False)

    class Meta:
        verbose_name = _('Follow-Up Escalated Reminder')
        verbose_name_plural = _('Follow-Up Escalated Reminders')
        ordering = ['due_date']

