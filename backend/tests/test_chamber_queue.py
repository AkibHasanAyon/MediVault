import pytest
import asyncio
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from channels.testing import WebsocketCommunicator

from apps.accounts.models import User
from apps.patients.models import PatientProfile
from apps.doctors.models import DoctorProfile
from apps.clinics.models import Clinic, ClinicAssistantProfile, ClinicDoctorAssociation
from apps.appointments.models import QueueEntry
from apps.appointments.consumers import broadcast_queue_event, async_broadcast_queue_event
from apps.notifications.services import MessagingService
from config.asgi import application


@pytest.mark.django_db(transaction=True)
class TestPhase7RealTimeChamberQueue:

    @pytest.fixture(autouse=True)
    def setup_entities(self):
        # 1. Clinic
        self.clinic = Clinic.objects.create(
            name="Popular Diagnostic Center",
            branch="Dhanmondi Branch",
            address="House 16, Road 2, Dhanmondi, Dhaka",
            contact_phone="+8801711000001",
        )

        # 2. Doctor (Profile auto-created by signals)
        self.doctor_user = User.objects.create_user(
            phone_number="+8801711000002",
            full_name="Prof. Dr. Rafiqul Islam",
            role=User.Role.DOCTOR,
            email="dr.rafiq@medivault.app",
        )
        self.doctor_profile = self.doctor_user.doctor_profile
        self.doctor_profile.bmdc_registration_number = "A-45678"
        self.doctor_profile.primary_specialty = "Cardiology"
        self.doctor_profile.chamber_address = "Room 304, Dhanmondi Branch"
        self.doctor_profile.is_verified_practitioner = True
        self.doctor_profile.save()

        self.doctor_jwt = str(RefreshToken.for_user(self.doctor_user).access_token)

        # Associate Doctor with Clinic
        self.association = ClinicDoctorAssociation.objects.create(
            clinic=self.clinic,
            doctor=self.doctor_profile,
            chamber_number="Room 304",
            session_days="Sat, Mon, Wed",
            session_start_time="17:00:00",
            session_end_time="21:00:00",
        )

        # 3. Assistant
        self.assistant_user = User.objects.create_user(
            phone_number="+8801711000003",
            full_name="Fatima Akter",
            role=User.Role.ASSISTANT,
            email="assistant.fatima@medivault.app",
        )
        self.assistant_profile = ClinicAssistantProfile.objects.create(
            user=self.assistant_user,
            clinic=self.clinic,
            desk_serial="Desk-1",
        )
        self.assistant_jwt = str(RefreshToken.for_user(self.assistant_user).access_token)

        # 4. Patients (Profile auto-created by signals)
        self.patient_user1 = User.objects.create_user(
            phone_number="+8801711000011",
            full_name="Abdul Karim",
            role=User.Role.PATIENT,
            email="abdul.karim@example.com",
        )
        self.patient_profile1 = self.patient_user1.patient_profile

        self.patient_user2 = User.objects.create_user(
            phone_number="+8801711000012",
            full_name="Nasreen Sultana",
            role=User.Role.PATIENT,
            email="nasreen.sultana@example.com",
        )
        self.patient_profile2 = self.patient_user2.patient_profile

        self.patient_jwt1 = str(RefreshToken.for_user(self.patient_user1).access_token)

    def test_websocket_connection_and_jwt_auth(self):
        """
        Task 7.1: Tests WebSocket connection with JWT token authentication and anonymous public display.
        """
        async def run_test():
            # 1. Connect with valid JWT token query param
            ws_url = f"/ws/queue/{self.clinic.id}/?token={self.assistant_jwt}"
            communicator = WebsocketCommunicator(application, ws_url)
            connected, _ = await communicator.connect()
            assert connected is True

            init_message = await communicator.receive_json_from()
            assert init_message["type"] == "CONNECTION_ESTABLISHED"
            assert init_message["authenticated"] is True
            assert init_message["clinic_id"] == str(self.clinic.id)

            # 2. Ping-Pong test
            await communicator.send_json_to({"action": "ping"})
            pong_res = await communicator.receive_json_from()
            assert pong_res["type"] == "PONG"

            await communicator.disconnect()

            # 3. Connect unauthenticated (Waiting Room TV / Public)
            public_url = f"/ws/queue/{self.clinic.id}/"
            public_communicator = WebsocketCommunicator(application, public_url)
            connected_pub, _ = await public_communicator.connect()
            assert connected_pub is True

            pub_init = await public_communicator.receive_json_from()
            assert pub_init["type"] == "CONNECTION_ESTABLISHED"
            assert pub_init["authenticated"] is False

            await public_communicator.disconnect()

        asyncio.run(run_test())

    def test_websocket_multi_client_broadcast(self):
        """
        Task 7.2: Tests broadcast propagation across multiple WebSocket clients connected to the same clinic.
        """
        async def run_test():
            comm1 = WebsocketCommunicator(application, f"/ws/queue/{self.clinic.id}/")
            comm2 = WebsocketCommunicator(application, f"/ws/queue/{self.clinic.id}/")

            await comm1.connect()
            await comm2.connect()

            # Discard initial connection greetings
            await comm1.receive_json_from()
            await comm2.receive_json_from()

            # Trigger channel layer broadcast
            await async_broadcast_queue_event(
                clinic_id=self.clinic.id,
                event_type='TOKEN_ISSUED',
                data={"token_display": "A-001", "patient_name": "Abdul Karim"},
                doctor_id=self.doctor_profile.id,
            )

            msg1 = await comm1.receive_json_from()
            msg2 = await comm2.receive_json_from()

            assert msg1["event"] == "TOKEN_ISSUED"
            assert msg1["data"]["token_display"] == "A-001"
            assert msg2["event"] == "TOKEN_ISSUED"
            assert msg2["data"]["patient_name"] == "Abdul Karim"

            await comm1.disconnect()
            await comm2.disconnect()

        asyncio.run(run_test())

    def test_assistant_assign_token_flow(self):
        """
        Task 7.3: Tests assistant assigning sequential daily tokens, wait estimation, and roster view.
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.assistant_jwt}")

        # 1. Assign token for Patient 1
        payload1 = {
            "patient_phone": "01711000011",
            "patient_name": "Abdul Karim",
            "doctor_id": str(self.doctor_profile.id),
        }
        res1 = client.post("/api/v1/assistant/queue/assign-token/", payload1, format='json')
        assert res1.status_code == 201
        data1 = res1.data
        assert data1["success"] is True
        assert data1["data"]["token_number"] == 1
        assert data1["data"]["token_display"] == "A-001"
        assert data1["data"]["state"] == "WAITING"
        assert data1["position_in_queue"] == 1
        assert data1["estimated_wait_minutes"] == 0

        # 2. Assign token for Patient 2 (sequential numbering)
        payload2 = {
            "patient_phone": "01711000012",
            "patient_name": "Nasreen Sultana",
            "doctor_id": str(self.doctor_profile.id),
        }
        res2 = client.post("/api/v1/assistant/queue/assign-token/", payload2, format='json')
        assert res2.status_code == 201
        data2 = res2.data
        assert data2["data"]["token_number"] == 2
        assert data2["data"]["token_display"] == "A-002"
        assert data2["position_in_queue"] == 2
        assert data2["estimated_wait_minutes"] == 7  # 1 waiting patient * 7 mins

        # 3. Retrieve today's roster
        res_roster = client.get("/api/v1/assistant/queue/today/")
        assert res_roster.status_code == 200
        roster_data = res_roster.data
        assert roster_data["success"] is True
        assert roster_data["count"] == 2
        assert roster_data["data"][0]["token_display"] == "A-001"
        assert roster_data["data"][1]["token_display"] == "A-002"

    def test_assistant_queue_status_update(self):
        """
        Task 7.3: Tests assistant updating token state to SKIPPED.
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.assistant_jwt}")

        entry = QueueEntry.objects.create(
            clinic=self.clinic,
            doctor=self.doctor_profile,
            patient=self.patient_profile1,
            token_number=1,
            queue_date=timezone.localdate(),
            state=QueueEntry.State.WAITING,
        )

        patch_res = client.patch(
            f"/api/v1/assistant/queue/{entry.id}/status/",
            {"state": "SKIPPED"},
            format='json'
        )
        assert patch_res.status_code == 200
        assert patch_res.data["data"]["state"] == "SKIPPED"

        entry.refresh_from_db()
        assert entry.state == QueueEntry.State.SKIPPED

    def test_doctor_live_queue_dashboard(self):
        """
        Task 7.4: Tests doctor's live in-chamber queue dashboard.
        """
        today = timezone.localdate()
        QueueEntry.objects.create(
            clinic=self.clinic,
            doctor=self.doctor_profile,
            patient=self.patient_profile1,
            token_number=1,
            queue_date=today,
            state=QueueEntry.State.IN_CHAMBER,
        )
        QueueEntry.objects.create(
            clinic=self.clinic,
            doctor=self.doctor_profile,
            patient=self.patient_profile2,
            token_number=2,
            queue_date=today,
            state=QueueEntry.State.WAITING,
        )

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.doctor_jwt}")

        res = client.get("/api/v1/doctor/queue/live/")
        assert res.status_code == 200
        data = res.data
        assert data["success"] is True
        assert data["current_patient"]["token_display"] == "A-001"
        assert len(data["next_waiting"]) == 1
        assert data["next_waiting"][0]["token_display"] == "A-002"
        assert data["stats"]["total_registered"] == 2
        assert data["stats"]["waiting_count"] == 1
        assert data["stats"]["in_consultation"] == 1

    def test_doctor_call_next_and_consultation_lifecycle(self):
        """
        Task 7.4: Tests doctor calling next patient, starting consultation, and completing consultation.
        """
        today = timezone.localdate()
        entry1 = QueueEntry.objects.create(
            clinic=self.clinic,
            doctor=self.doctor_profile,
            patient=self.patient_profile1,
            token_number=1,
            queue_date=today,
            state=QueueEntry.State.WAITING,
        )

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.doctor_jwt}")

        # 1. Call next patient
        call_res = client.post("/api/v1/doctor/queue/call-next/")
        assert call_res.status_code == 200
        assert call_res.data["success"] is True
        assert call_res.data["data"]["token_display"] == "A-001"
        assert call_res.data["data"]["state"] == "CALLED_IN"

        entry1.refresh_from_db()
        assert entry1.state == QueueEntry.State.CALLED_IN
        assert entry1.called_at is not None

        # 2. Start consultation (patient enters chamber)
        start_res = client.post(f"/api/v1/doctor/queue/{entry1.id}/start-consultation/")
        assert start_res.status_code == 200
        entry1.refresh_from_db()
        assert entry1.state == QueueEntry.State.IN_CHAMBER

        # 3. Finish consultation
        finish_res = client.post(f"/api/v1/doctor/queue/{entry1.id}/finish-consultation/")
        assert finish_res.status_code == 200
        entry1.refresh_from_db()
        assert entry1.state == QueueEntry.State.DONE
        assert entry1.completed_at is not None

    def test_automated_serial_call_and_proximity_alerts(self, monkeypatch):
        """
        Task 7.5: Tests that calling token A-001 triggers direct call-in alert to token 1
        and automated proximity alert to token 3 (who has 2 patients ahead).
        """
        today = timezone.localdate()
        e1 = QueueEntry.objects.create(
            clinic=self.clinic, doctor=self.doctor_profile, patient=self.patient_profile1,
            token_number=1, queue_date=today, state=QueueEntry.State.WAITING
        )
        e2 = QueueEntry.objects.create(
            clinic=self.clinic, doctor=self.doctor_profile, patient=self.patient_profile2,
            token_number=2, queue_date=today, state=QueueEntry.State.WAITING
        )
        # Create Patient 3
        u3 = User.objects.create_user(
            phone_number="+8801711000013", full_name="Habib Ullah", role=User.Role.PATIENT, email="habib@example.com"
        )
        e3 = QueueEntry.objects.create(
            clinic=self.clinic, doctor=self.doctor_profile, patient=u3.patient_profile,
            token_number=3, queue_date=today, state=QueueEntry.State.WAITING
        )

        sent_call_ins = []
        sent_queue_alerts = []

        monkeypatch.setattr(MessagingService, 'send_call_in_alert', lambda **kwargs: sent_call_ins.append(kwargs) or True)
        monkeypatch.setattr(MessagingService, 'send_queue_alert', lambda **kwargs: sent_queue_alerts.append(kwargs) or True)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.doctor_jwt}")

        res = client.post("/api/v1/doctor/queue/call-next/")
        assert res.status_code == 200

        # Check direct call-in alert delivered to e1 (A-001)
        assert len(sent_call_ins) == 1
        assert sent_call_ins[0]["serial_token"] == "A-001"
        assert sent_call_ins[0]["recipient_phone"] == self.patient_user1.phone_number

        # Check proximity alert delivered to e3 (A-003, remaining_ahead = 2)
        assert len(sent_queue_alerts) == 1
        assert sent_queue_alerts[0]["serial_token"] == "A-003"
        assert sent_queue_alerts[0]["remaining_ahead"] == 2
        assert sent_queue_alerts[0]["recipient_phone"] == u3.phone_number

    def test_clinic_chamber_analytics_and_display(self):
        """
        Task 7.6: Tests end-of-day chamber analytics and public waiting room TV display endpoint.
        """
        today = timezone.localdate()
        now = timezone.now()

        # Seed entries with timestamps (use update to set created_at bypassing auto_now_add)
        e1 = QueueEntry.objects.create(
            clinic=self.clinic,
            doctor=self.doctor_profile,
            patient=self.patient_profile1,
            token_number=1,
            queue_date=today,
            state=QueueEntry.State.DONE,
            called_at=now - timedelta(minutes=30),
            completed_at=now - timedelta(minutes=15),
        )
        QueueEntry.objects.filter(id=e1.id).update(created_at=now - timedelta(minutes=45))

        e2 = QueueEntry.objects.create(
            clinic=self.clinic,
            doctor=self.doctor_profile,
            patient=self.patient_profile2,
            token_number=2,
            queue_date=today,
            state=QueueEntry.State.CALLED_IN,
            called_at=now - timedelta(minutes=5),
        )
        QueueEntry.objects.filter(id=e2.id).update(created_at=now - timedelta(minutes=20))

        # 1. Assistant Daily Summary
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.assistant_jwt}")

        sum_res = client.get(f"/api/v1/assistant/queue/daily-summary/?clinic_id={self.clinic.id}")
        assert sum_res.status_code == 200
        metrics = sum_res.data["metrics"]
        assert metrics["total_registered"] == 2
        assert metrics["total_completed"] == 1
        assert metrics["total_in_chamber"] == 1
        assert metrics["avg_wait_minutes"] > 0
        assert metrics["avg_consultation_minutes"] > 0

        # 2. Public Waiting Room TV Display
        anon_client = APIClient()
        disp_res = anon_client.get(f"/api/v1/queue/display/{self.clinic.id}/")
        assert disp_res.status_code == 200
        disp_data = disp_res.data
        assert disp_data["success"] is True
        assert disp_data["clinic_name"] == "Popular Diagnostic Center"
        assert len(disp_data["chambers"]) == 1
        chamber = disp_data["chambers"][0]
        assert chamber["doctor_name"] == "Prof. Dr. Rafiqul Islam"
        assert chamber["chamber_number"] == "Room 304"
        assert chamber["current_token"] == "A-002"
        assert chamber["current_state"] == "CALLED_IN"
