import logging
from apps.sharing.models import ConsultationShare, ShareAuditLog
from apps.doctors.models import DoctorProfile

logger = logging.getLogger('medivault.sharing')

class AuditService:
    """
    Maintains an immutable audit log for clinical data access under consultation shares.
    """

    @staticmethod
    def log_access(
        share: ConsultationShare,
        doctor: DoctorProfile,
        ip_address: str | None = None,
        user_agent: str = "",
        action_summary: str = "Accessed patient medical records via QR scan"
    ) -> ShareAuditLog:
        audit_entry = ShareAuditLog.objects.create(
            share=share,
            doctor=doctor,
            ip_address=ip_address,
            user_agent=user_agent[:255] if user_agent else "",
            action_summary=action_summary
        )
        logger.info(
            "Audit Log: Dr. %s (BMDC: %s) accessed records of %s under share %s",
            doctor.user.full_name, doctor.bmdc_number, share.patient.user.full_name, share.id
        )
        return audit_entry

