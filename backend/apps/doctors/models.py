from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel

class DoctorProfile(TimeStampedUUIDModel):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='doctor_profile')
    bmdc_registration_number = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("BM&DC Medical License Number")
    )
    degrees_qualifications = models.CharField(
        max_length=255,
        help_text=_("e.g. MBBS, FCPS, MD (Internal Medicine)")
    )
    primary_specialty = models.CharField(max_length=100, db_index=True)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    bio = models.TextField(blank=True)
    chamber_address = models.TextField(blank=True)
    is_verified_practitioner = models.BooleanField(default=False, db_index=True)

    @property
    def specialties(self):
        return self.primary_specialty

    @specialties.setter
    def specialties(self, val):
        self.primary_specialty = val

    @property
    def is_verified(self):
        return self.is_verified_practitioner

    @is_verified.setter
    def is_verified(self, val):
        self.is_verified_practitioner = val

    class Meta:
        verbose_name = _('Doctor Profile')
        verbose_name_plural = _('Doctor Profiles')
        ordering = ['user__full_name']

    def __str__(self):
        status = "Verified" if self.is_verified_practitioner else "Pending"
        return f"Dr. {self.user.full_name} ({self.primary_specialty}) - [{status}]"

