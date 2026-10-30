import logging
from django.utils import timezone
from apps.notifications.services import MessagingService

logger = logging.getLogger('medivault.appointments.queue_notifier')


class QueueNotifierService:
    """
    Automated Serial Call-In and Queue Proximity Alert Engine.
    Dispatches:
    1. Direct Call-In Alert to the patient whose token is called.
    2. Proximity Alert to patients who are 2 serials away from entering the chamber.
    """

    @classmethod
    def notify_patient_called(cls, queue_entry) -> bool:
        """
        Notifies the patient that their serial token has been called to enter the doctor's chamber.
        """
        try:
            patient_user = queue_entry.patient.user
            doctor_user = queue_entry.doctor.user
            clinic = queue_entry.clinic

            return MessagingService.send_call_in_alert(
                recipient_phone=patient_user.phone_number,
                recipient_email=patient_user.email,
                serial_token=queue_entry.token_display,
                clinic_name=clinic.name,
                doctor_name=doctor_user.full_name,
            )
        except Exception as e:
            logger.error("Failed to dispatch call-in notification for entry %s: %s", queue_entry.id, str(e))
            return False

    @classmethod
    def notify_upcoming_patients(cls, clinic_id, doctor_id, current_queue_entry, queue_date=None, target_ahead: int = 2) -> list[str]:
        """
        Queries upcoming WAITING patients for this doctor today and notifies patients who are
        'target_ahead' positions away (default 2 patients ahead).
        """
        from apps.appointments.models import QueueEntry

        if not queue_date:
            queue_date = current_queue_entry.queue_date if current_queue_entry else timezone.localdate()

        waiting_entries = QueueEntry.objects.filter(
            clinic_id=clinic_id,
            doctor_id=doctor_id,
            queue_date=queue_date,
            state=QueueEntry.State.WAITING,
        ).exclude(id=current_queue_entry.id if current_queue_entry else None).order_by('token_number').select_related('patient__user', 'clinic')

        alerted_tokens = []

        for index, entry in enumerate(waiting_entries):
            # index 0 means 1 patient ahead (the one in chamber),
            # index 1 means 2 patients ahead (the one in chamber + index 0 waiting)
            # When index + 1 == target_ahead, this patient has target_ahead patients ahead of them
            remaining_ahead = index + 1
            if remaining_ahead == target_ahead:
                try:
                    patient_user = entry.patient.user
                    clinic_name = entry.clinic.name
                    MessagingService.send_queue_alert(
                        recipient_phone=patient_user.phone_number,
                        recipient_email=patient_user.email,
                        serial_token=entry.token_display,
                        remaining_ahead=remaining_ahead,
                        clinic_name=clinic_name,
                    )
                    alerted_tokens.append(entry.token_display)
                    logger.info("Sent proximity alert to token %s (%d ahead)", entry.token_display, remaining_ahead)
                except Exception as e:
                    logger.error("Failed sending proximity alert to token %s: %s", entry.token_display, str(e))

        return alerted_tokens

