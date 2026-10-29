from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel

class MonthlyHealthReport(TimeStampedUUIDModel):
    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='monthly_reports')
    report_year = models.PositiveSmallIntegerField()
    report_month = models.PositiveSmallIntegerField(help_text=_("Calendar month (1-12)"))
    report_title = models.CharField(max_length=255)
    
    # Aggregated metrics (deterministic math)
    glucose_readings_count = models.PositiveIntegerField(default=0)
    glucose_average_mmol = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    bp_readings_count = models.PositiveIntegerField(default=0)
    danger_alerts_count = models.PositiveIntegerField(default=0)
    adherence_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    # AI Clinical Narrative
    ai_summary_narrative = models.TextField(blank=True)
    pdf_file = models.FileField(upload_to='monthly_reports/%Y/%m/', blank=True, null=True)

    class Meta:
        verbose_name = _('Monthly Health Report')
        verbose_name_plural = _('Monthly Health Reports')
        unique_together = ('patient', 'report_year', 'report_month')
        ordering = ['-report_year', '-report_month']

    def __str__(self):
        return f"Report {self.report_year}-{self.report_month:02d} for {self.patient.user.full_name}"

