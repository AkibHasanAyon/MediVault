import logging
from datetime import datetime, timedelta
from celery import shared_task
from django.utils import timezone

from .models import MedicationReminder
from apps.notifications.services import MessagingService

logger = logging.getLogger('medivault.medications')

@shared_task
def dispatch_scheduled_medication_reminders():
    """
    Periodic Celery Beat task (e.g. running every 15 mins).
    Scans for active medication reminders scheduled within the current time window,
    and dispatches multichannel notifications (email/push/SMS).
    """
    now = timezone.localtime()

    # Match reminders in the current window (+/- 7.5 mins or matching hour and minute window)
    window_start = (now - timedelta(minutes=8)).time()
    window_end = (now + timedelta(minutes=7)).time()

    reminders = MedicationReminder.objects.filter(
        is_enabled=True,
        medication__is_active=True,
        reminder_time__gte=window_start,
        reminder_time__lte=window_end
    ).select_related('medication__patient__user', 'medication__family_member')

    dispatched_count = 0
    for reminder in reminders:
        try:
            med = reminder.medication
            patient_user = med.patient.user
            target_name = med.family_member.full_name if med.family_member else patient_user.full_name
            phone = patient_user.phone_number
            email = patient_user.email
            time_str = reminder.reminder_time.strftime('%I:%M %p')

            MessagingService.send_medication_reminder(
                recipient_phone=phone,
                recipient_email=email,
                patient_name=target_name,
                medication_name=med.name,
                strength=med.strength,
                time_str=time_str
            )
            dispatched_count += 1
            logger.info("Dispatched medication reminder for %s (%s) to %s", med.name, time_str, target_name)
        except Exception as e:
            logger.error("Failed to dispatch reminder %s: %s", reminder.id, str(e))

    logger.info("Total medication reminders dispatched in current window: %d", dispatched_count)
    return dispatched_count

