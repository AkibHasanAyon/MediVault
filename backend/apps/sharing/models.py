from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel

class ConsultationShare(TimeStampedUUIDModel):
    """
    Ephemeral 30-minute QR Consultation Session.
    Binds patient authorization to consulting doctor with strict TTL.
    """
    patient = models.ForeignKey('patients.PatientProfile', on_delete=models.CASCADE, related_name='authorized_shares')
    doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE, null=True, blank=True, related_name='consultation_shares')
    token_hash = models.CharField(max_length=128, unique=True, db_index=True)
    permitted_scope = models.JSONField(
        default=dict,
        help_text=_("Scoped array of permitted record types or IDs e.g. {'documents': true, 'vitals_90d': true}")
    )
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = _('Consultation Share Session')
        verbose_name_plural = _('Consultation Share Sessions')
        ordering = ['-created_at']

    def __str__(self):
        doctor_name = self.doctor.user.full_name if self.doctor else "Unclaimed"
        return f"Share: {self.patient.user.full_name} -> Dr. {doctor_name} (Expires: {self.expires_at.strftime('%H:%M:%S')})"


class ShareAuditLog(TimeStampedUUIDModel):
    """Immutable audit trail for every doctor access event under a ConsultationShare."""
    share = models.ForeignKey(ConsultationShare, on_delete=models.CASCADE, related_name='audit_logs')
    doctor = models.ForeignKey('doctors.DoctorProfile', on_delete=models.CASCADE, related_name='share_audit_logs')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    action_summary = models.CharField(max_length=255, default='Accessed patient records')

    class Meta:
        verbose_name = _('Share Audit Log')
        verbose_name_plural = _('Share Audit Logs')
        ordering = ['-created_at']

    def __str__(self):
        return f"Dr. {self.doctor.user.full_name} viewed {self.share.patient.user.full_name} at {self.created_at}"

