import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel

class PatientProfile(TimeStampedUUIDModel):
    class BloodGroup(models.TextChoices):
        A_POS = 'A+', 'A+'
        A_NEG = 'A-', 'A-'
        B_POS = 'B+', 'B+'
        B_NEG = 'B-', 'B-'
        AB_POS = 'AB+', 'AB+'
        AB_NEG = 'AB-', 'AB-'
        O_POS = 'O+', 'O+'
        O_NEG = 'O-', 'O-'
        UNKNOWN = 'UNKNOWN', 'Unknown'

    class Gender(models.TextChoices):
        MALE = 'MALE', _('Male')
        FEMALE = 'FEMALE', _('Female')
        OTHER = 'OTHER', _('Other')

    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='patient_profile')
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, default=Gender.MALE)
    blood_group = models.CharField(max_length=10, choices=BloodGroup.choices, default=BloodGroup.UNKNOWN)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True)
    known_allergies = models.TextField(blank=True, default="None reported", help_text=_("Reported food and drug allergies"))

    class Meta:
        verbose_name = _('Patient Profile')
        verbose_name_plural = _('Patient Profiles')

    def __str__(self):
        return f"Patient: {self.user.full_name} ({self.user.phone_number})"


class FamilyMember(TimeStampedUUIDModel):
    MAX_FAMILY_MEMBERS = 8

    class Relationship(models.TextChoices):
        PARENT = 'PARENT', _('Parent')
        SPOUSE = 'SPOUSE', _('Spouse')
        CHILD = 'CHILD', _('Child')
        SIBLING = 'SIBLING', _('Sibling')
        OTHER = 'OTHER', _('Other')

    primary_account = models.ForeignKey(PatientProfile, on_delete=models.CASCADE, related_name='family_members')
    full_name = models.CharField(max_length=255)
    relationship = models.CharField(max_length=20, choices=Relationship.choices)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=PatientProfile.Gender.choices, default=PatientProfile.Gender.MALE)
    blood_group = models.CharField(max_length=10, choices=PatientProfile.BloodGroup.choices, default=PatientProfile.BloodGroup.UNKNOWN)
    known_allergies = models.TextField(blank=True, default="None reported")

    class Meta:
        verbose_name = _('Family Member')
        verbose_name_plural = _('Family Members')
        ordering = ['full_name']

    def clean(self):
        super().clean()
        if self._state.adding:
            current_count = FamilyMember.objects.filter(primary_account=self.primary_account).count()
            if current_count >= self.MAX_FAMILY_MEMBERS:
                raise ValidationError(
                    f"A primary account cannot manage more than {self.MAX_FAMILY_MEMBERS} family member profiles."
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.relationship} of {self.primary_account.user.full_name})"
