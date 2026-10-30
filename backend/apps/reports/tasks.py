import logging
from datetime import date
from celery import shared_task
from django.utils import timezone

from apps.patients.models import PatientProfile
from .services.pdf_builder import MonthlyReportBuilder
from apps.notifications.services import MessagingService

logger = logging.getLogger('medivault.reports')

@shared_task
def generate_monthly_health_reports():
    """
    Celery Beat task running on the 1st of each month.
    Generates health summary reports for the previous calendar month for all active patients.
    """
    today = timezone.localdate()
    # Target previous month
    if today.month == 1:
        target_year = today.year - 1
        target_month = 12
    else:
        target_year = today.year
        target_month = today.month - 1

    patients = PatientProfile.objects.select_related('user').all()
    generated_count = 0

    for patient in patients:
        try:
            report = MonthlyReportBuilder.generate_monthly_report(patient, target_year, target_month)
            generated_count += 1

            # Dispatch notification
            user = patient.user
            if user.email:
                MessagingService.send_otp(
                    recipient_phone=user.phone_number,
                    recipient_email=user.email,
                    otp_code="REPORT_READY",
                    user_name=user.full_name
                )
        except Exception as e:
            logger.error("Failed to generate monthly report for patient %s: %s", patient.id, str(e))

    logger.info("Generated %d monthly health reports for %d-%02d", generated_count, target_year, target_month)
    return generated_count

