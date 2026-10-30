import logging
from datetime import date, timedelta
from django.utils import timezone

from apps.appointments.models import FollowUpReminder
from apps.prescriptions.models import Prescription

logger = logging.getLogger('medivault.prescriptions')

class FollowUpService:
    """
    Manages follow-up memory and milestone escalation reminders:
    - Milestone 1: 2.5 months before (early notice for long-interval follow-ups)
    - Milestone 2: 1 week before
    - Milestone 3: Due date
    """

    @classmethod
    def schedule_follow_up_milestones(cls, prescription: Prescription) -> list[FollowUpReminder]:
        if not prescription.follow_up_date:
            return []

        due_date = prescription.follow_up_date
        today = timezone.localdate()
        days_ahead = (due_date - today).days

        created_reminders = []

        # 1. Milestone 1: 2.5 Months Before (if follow-up is at least 80 days away)
        if days_ahead >= 80:
            early_date = due_date - timedelta(days=75)
            r1, _ = FollowUpReminder.objects.get_or_create(
                prescription=prescription,
                milestone_stage=FollowUpReminder.Milestone.TWO_MONTHS_BEFORE,
                defaults={
                    "patient": prescription.patient,
                    "doctor": prescription.doctor,
                    "due_date": early_date,
                    "is_dispatched": False,
                }
            )
            created_reminders.append(r1)

        # 2. Milestone 2: 1 Week Before (if follow-up is at least 8 days away)
        if days_ahead >= 8:
            week_date = due_date - timedelta(days=7)
            r2, _ = FollowUpReminder.objects.get_or_create(
                prescription=prescription,
                milestone_stage=FollowUpReminder.Milestone.ONE_WEEK_BEFORE,
                defaults={
                    "patient": prescription.patient,
                    "doctor": prescription.doctor,
                    "due_date": week_date,
                    "is_dispatched": False,
                }
            )
            created_reminders.append(r2)

        # 3. Milestone 3: Exact Due Date
        r3, _ = FollowUpReminder.objects.get_or_create(
            prescription=prescription,
            milestone_stage=FollowUpReminder.Milestone.DUE_DATE,
            defaults={
                "patient": prescription.patient,
                "doctor": prescription.doctor,
                "due_date": due_date,
                "is_dispatched": False,
            }
        )
        created_reminders.append(r3)

        logger.info(
            "Scheduled %d follow-up milestone reminders for prescription %s (Due: %s)",
            len(created_reminders), prescription.id, due_date
        )
        return created_reminders

