import logging
from celery import shared_task
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import DangerAlert
from apps.notifications.services import MessagingService

logger = logging.getLogger('medivault.alerts')

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def dispatch_danger_alert_task(self, alert_id: str):
    """
    Dispatches immediate multichannel emergency danger alerts:
    1. Real-time WebSocket broadcast to user's alert channel (in-app HUD flash).
    2. Urgent SMS/SMTP email dispatch via MessagingService with 999 emergency info.
    """
    try:
        alert = DangerAlert.objects.select_related('patient__user', 'family_member').get(id=alert_id)
        patient_user = alert.patient.user
        target_name = alert.family_member.full_name if alert.family_member else patient_user.full_name

        # 1. Real-time WebSocket event via Django Channels
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                group_name = f"user_{patient_user.id}_alerts"
                payload = {
                    "type": "danger.alert",
                    "data": {
                        "alert_id": str(alert.id),
                        "alert_type": alert.alert_type,
                        "trigger_value": alert.trigger_value,
                        "instruction_text": alert.instruction_text,
                        "patient_name": target_name,
                        "created_at": alert.created_at.isoformat(),
                    }
                }
                async_to_sync(channel_layer.group_send)(group_name, payload)
                logger.info("Broadcasted danger alert %s to WebSocket group %s", alert.id, group_name)
        except Exception as ws_err:
            logger.warning("WebSocket alert broadcast skipped or channel layer offline: %s", str(ws_err))

        # 2. Out-of-band notification dispatch (Email in dev/SMS in prod)
        phone = alert.patient.emergency_contact_phone or patient_user.phone_number
        email = patient_user.email

        dispatched = MessagingService.send_danger_alert(
            recipient_phone=phone,
            recipient_email=email,
            alert_type=alert.alert_type,
            trigger_value=alert.trigger_value,
            instructions=alert.instruction_text
        )

        alert.notification_dispatched = dispatched
        alert.save(update_fields=['notification_dispatched'])
        logger.info("Dispatched emergency alert notification for alert %s (Dispatched=%s)", alert.id, dispatched)

    except DangerAlert.DoesNotExist:
        logger.error("DangerAlert %s not found for dispatch task", alert_id)
    except Exception as exc:
        logger.error("Error dispatching danger alert %s: %s", alert_id, str(exc))
        raise self.retry(exc=exc)

