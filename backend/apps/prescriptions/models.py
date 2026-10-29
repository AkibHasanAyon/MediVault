from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel

class Prescription(TimeStampedUUIDModel):
    doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE, related_name='issued_prescriptions')
    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='digital_prescriptions')
    family_member = models.ForeignKey('patients.FamilyMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='digital_prescriptions')
    clinic = models.ForeignKey('clinics.Clinic', on_delete=models.SET_NULL, null=True, blank=True, related_name='prescriptions')
    
    chief_complaints = models.TextField()
    clinical_findings = models.TextField(blank=True)
    diagnosis = models.TextField()
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.CharField(max_length=255, blank=True, help_text=_("e.g. Return after 3 months"))
    pdf_file = models.FileField(upload_to='digital_prescriptions/%Y/%m/', blank=True, null=True)

    class Meta:
        verbose_name = _('Digital Prescription')
        verbose_name_plural = _('Digital Prescriptions')
        ordering = ['-created_at']

    def __str__(self):
        target = self.family_member.full_name if self.family_member else self.patient.user.full_name
        return f"Prescription for {target} by Dr. {self.doctor.user.full_name} ({self.created_at.strftime('%Y-%m-%d')})"


class PrescriptionMedication(TimeStampedUUIDModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='medications')
    brand_name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255, blank=True)
    dosage_form = models.CharField(max_length=50, default='Tablet', help_text=_("Tablet, Capsule, Syrup, Injection"))
    strength = models.CharField(max_length=50, help_text=_("e.g. 500mg, 10mg, 20ml"))
    frequency = models.CharField(max_length=50, help_text=_("e.g. 1+0+1 or Once Daily"))
    timing_relation = models.CharField(max_length=50, default='After Food', help_text=_("Before Food, After Food, With Food"))
    duration_days = models.PositiveSmallIntegerField(default=30)
    special_instructions = models.TextField(blank=True)

    class Meta:
        verbose_name = _('Prescription Medication Item')
        verbose_name_plural = _('Prescription Medication Items')

    def __str__(self):
        return f"{self.brand_name} {self.strength} ({self.frequency})"


class DrugInteractionRule(TimeStampedUUIDModel):
    class Severity(models.TextChoices):
        CONTRAINDICATED = 'CONTRAINDICATED', _('Contraindicated / Dangerous')
        SEVERE = 'SEVERE', _('Severe Interaction')
        MODERATE = 'MODERATE', _('Moderate Caution')
        INFO = 'INFO', _('Informational Notice')

    drug_a_generic = models.CharField(max_length=150, db_index=True)
    drug_b_generic = models.CharField(max_length=150, db_index=True)
    severity = models.CharField(max_length=20, choices=Severity.choices, default=Severity.MODERATE)
    clinical_effect = models.TextField(help_text=_("Explanation of adverse effect e.g. Increased hypoglycemia risk"))
    management_advice = models.TextField(help_text=_("Recommended physician action e.g. Adjust dose, monitor glucose"))

    class Meta:
        verbose_name = _('Drug Interaction Rule')
        verbose_name_plural = _('Drug Interaction Rules')
        unique_together = ('drug_a_generic', 'drug_b_generic')

    def __str__(self):
        return f"[{self.severity}] {self.drug_a_generic} + {self.drug_b_generic}"

