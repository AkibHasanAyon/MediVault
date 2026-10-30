import logging
from celery import shared_task
from django.utils import timezone
from apps.appointments.models import FollowUpReminder
from apps.notifications.services import MessagingService

logger = logging.getLogger('medivault.prescriptions')

@shared_task
def dispatch_scheduled_follow_up_reminders():
    """
    Periodic Celery Beat task running daily.
    Dispatches due escalated follow-up reminders (2.5 months, 1 week, due date)
    via email / SMS.
    """
    today = timezone.localdate()
    due_reminders = FollowUpReminder.objects.filter(
        due_date__lte=today,
        is_dispatched=False
    ).select_related('patient__user', 'doctor__user', 'prescription')

    dispatched_count = 0
    for reminder in due_reminders:
        try:
            patient_user = reminder.patient.user
            doctor_name = f"Dr. {reminder.doctor.user.full_name}"

            if reminder.milestone_stage == FollowUpReminder.Milestone.DUE_DATE:
                subject_stage = "Due Today"
                msg_body = f"Your scheduled medical follow-up consultation with {doctor_name} is due today."
            elif reminder.milestone_stage == FollowUpReminder.Milestone.ONE_WEEK_BEFORE:
                subject_stage = "Upcoming Next Week"
                msg_body = f"Reminder: Your medical follow-up with {doctor_name} is scheduled for next week ({reminder.prescription.follow_up_date})."
            else:
                subject_stage = "Advance Health Notice"
                msg_body = f"Advance Notice: Your periodic health review with {doctor_name} is approaching ({reminder.prescription.follow_up_date})."

            full_msg = f"{msg_body} Please book your appointment at your earliest convenience."

            # Dispatch notification
            MessagingService.send_danger_alert(
                recipient_phone=patient_user.phone_number,
                recipient_email=patient_user.email,
                alert_type=f"Follow-Up Reminder ({subject_stage})",
                trigger_value=str(reminder.due_date),
                instructions=full_msg
            )

            reminder.is_dispatched = True
            reminder.save(update_fields=['is_dispatched'])
            dispatched_count += 1
            logger.info("Dispatched follow-up reminder %s to %s", reminder.id, patient_user.phone_number)
        except Exception as e:
            logger.error("Failed to dispatch follow-up reminder %s: %s", reminder.id, str(e))

    logger.info("Total follow-up reminders dispatched: %d", dispatched_count)
    return dispatched_count

