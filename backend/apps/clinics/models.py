from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel

class Clinic(TimeStampedUUIDModel):
    name = models.CharField(max_length=255, db_index=True)
    branch = models.CharField(max_length=100, blank=True)
    address = models.TextField()
    contact_phone = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = _('Clinic / Chamber')
        verbose_name_plural = _('Clinics / Chambers')
        ordering = ['name', 'branch']

    def __str__(self):
        return f"{self.name}{f' ({self.branch})' if self.branch else ''}"


class ClinicAssistantProfile(TimeStampedUUIDModel):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='assistant_profile')
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='assistants')
    desk_serial = models.CharField(max_length=50, blank=True, help_text=_("Desk identification e.g. Desk-1"))
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _('Clinic Assistant Profile')
        verbose_name_plural = _('Clinic Assistant Profiles')

    def __str__(self):
        return f"Assistant: {self.user.full_name} ({self.clinic.name})"


class ClinicDoctorAssociation(TimeStampedUUIDModel):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='doctor_associations')
    doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE, related_name='clinic_associations')
    chamber_number = models.CharField(max_length=50, blank=True)
    session_days = models.CharField(max_length=100, help_text=_("e.g. Sat, Mon, Wed"))
    session_start_time = models.TimeField()
    session_end_time = models.TimeField()

    class Meta:
        verbose_name = _('Clinic-Doctor Chamber Association')
        verbose_name_plural = _('Clinic-Doctor Chamber Associations')
        unique_together = ('clinic', 'doctor')

    def __str__(self):
        return f"Dr. {self.doctor.user.full_name} at {self.clinic.name} ({self.session_days})"

