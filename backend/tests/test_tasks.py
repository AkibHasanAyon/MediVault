import pytest
import asyncio
from datetime import timedelta
from django.utils import timezone
from channels.testing import WebsocketCommunicator

from tests.factories import (
    UserFactory,
    PatientProfileFactory,
    DoctorProfileFactory,
    ClinicFactory,
    PrescriptionFactory,
)
from apps.accounts.models import User
from apps.medications.models import Medication, MedicationReminder
from apps.appointments.models import FollowUpReminder
from apps.medications.tasks import dispatch_scheduled_medication_reminders
from apps.prescriptions.tasks import dispatch_scheduled_follow_up_reminders
from apps.reports.tasks import generate_monthly_health_reports
from apps.appointments.consumers import async_broadcast_queue_event
from config.asgi import application


@pytest.mark.django_db(transaction=True)
class TestPhase9CeleryAndChannelsConcurrency:

    @pytest.fixture(autouse=True)
    def setup_data(self):
        self.clinic = ClinicFactory.create()
        self.patient_user = UserFactory.create(role=User.Role.PATIENT)
        self.patient_profile = self.patient_user.patient_profile

        self.doctor_user = UserFactory.create(role=User.Role.DOCTOR)
        self.doctor_profile = self.doctor_user.doctor_profile

    def test_celery_medication_reminders_task(self):
        """Tests that dispatch_scheduled_medication_reminders executes without exceptions."""
        med = Medication.objects.create(
            patient=self.patient_profile,
            name="Metformin HCl",
            generic_name="Metformin",
            strength="500mg",
            dosage_pattern="1+0+1",
            start_date=timezone.localdate(),
            is_active=True,
        )

        now = timezone.localtime()
        # Schedule reminder in current slot
        reminder = MedicationReminder.objects.create(
            medication=med,
            reminder_time=now.time(),
            is_enabled=True,
        )

        # Execute Celery task
        result = dispatch_scheduled_medication_reminders()
        assert result is not None

    def test_celery_follow_up_reminders_task(self):
        """Tests that dispatch_scheduled_follow_up_reminders runs and updates milestones."""
        today = timezone.localdate()
        reminder = FollowUpReminder.objects.create(
            patient=self.patient_profile,
            doctor=self.doctor_profile,
            due_date=today,
            milestone_stage=FollowUpReminder.Milestone.DUE_DATE,
            is_dispatched=False,
        )

        result = dispatch_scheduled_follow_up_reminders()
        assert result is not None

        reminder.refresh_from_db()
        assert reminder.is_dispatched is True

    def test_celery_monthly_reports_task(self):
        """Tests that generate_monthly_health_reports runs across active patients."""
        result = generate_monthly_health_reports()
        assert result is not None
        assert isinstance(result, (int, dict, str))

    def test_channels_websocket_concurrency(self):
        """
        Tests WebSocket concurrency: multiple communicators simultaneously connected
        and receiving broadcast queue events without dropping messages.
        """
        async def run_concurrent_test():
            clients = [
                WebsocketCommunicator(application, f"/ws/queue/{self.clinic.id}/")
                for _ in range(4)
            ]

            # Connect all 4 clients concurrently
            connect_results = await asyncio.gather(*(c.connect() for c in clients))
            for connected, _ in connect_results:
                assert connected is True

            # Discard initial connection greetings
            await asyncio.gather(*(c.receive_json_from() for c in clients))

            # Broadcast concurrent event
            payload_data = {"token_display": "A-099", "state": "CALLED_IN"}
            await async_broadcast_queue_event(
                clinic_id=self.clinic.id,
                event_type="PATIENT_CALLED",
                data=payload_data,
            )

            # Verify all 4 clients receive the broadcast
            messages = await asyncio.gather(*(c.receive_json_from() for c in clients))
            for msg in messages:
                assert msg["event"] == "PATIENT_CALLED"
                assert msg["data"]["token_display"] == "A-099"

            # Disconnect all
            await asyncio.gather(*(c.disconnect() for c in clients))

        asyncio.run(run_concurrent_test())
