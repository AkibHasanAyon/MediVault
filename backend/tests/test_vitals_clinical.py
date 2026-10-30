import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from tests.factories import UserFactory
from apps.accounts.models import User
from apps.health_logs.models import BloodGlucoseLog, BloodPressureLog, DangerAlert


@pytest.mark.django_db
class TestPhase9ClinicalDataAndVitalsSafety:

    @pytest.fixture(autouse=True)
    def setup_patient(self):
        self.patient_user = UserFactory.create(role=User.Role.PATIENT)
        self.patient_profile = self.patient_user.patient_profile
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(self.patient_user).access_token}")

    def test_hypoglycemia_trigger(self):
        """Logging glucose < 3.9 mmol/L flags danger and creates HYPOGLYCEMIA alert."""
        res = self.client.post('/api/v1/health-logs/blood-glucose/', {
            "glucose_value_mmol": "2.9",
            "reading_type": "FASTING",
            "notes": "Feeling dizzy and shaky",
        })
        assert res.status_code == 201
        assert res.data["is_danger"] is True

        log = BloodGlucoseLog.objects.get(id=res.data["id"])
        assert log.is_danger is True

        alert = DangerAlert.objects.filter(patient=self.patient_profile).first()
        assert alert is not None
        assert alert.alert_type == DangerAlert.AlertType.HYPOGLYCEMIA
        assert "sugar" in alert.instruction_text.lower() or "hypoglycemia" in alert.instruction_text.lower()

    def test_hyperglycemia_trigger(self):
        """Logging glucose > 16.0 mmol/L flags danger and creates HYPERGLYCEMIA alert."""
        res = self.client.post('/api/v1/health-logs/blood-glucose/', {
            "glucose_value_mmol": "18.2",
            "reading_type": "POST_MEAL",
        })
        assert res.status_code == 201
        assert res.data["is_danger"] is True

        alert = DangerAlert.objects.filter(
            patient=self.patient_profile,
            alert_type=DangerAlert.AlertType.HYPERGLYCEMIA
        ).first()
        assert alert is not None
        assert alert.notification_dispatched is True

    def test_hypertensive_crisis_or_logic(self):
        """
        Systolic > 180 OR Diastolic > 120 mmHg triggers Hypertensive Crisis alert.
        Tests all 4 boundary conditions.
        """
        # Case 1: Systolic > 180, Diastolic normal (185/85) -> CRISIS
        r1 = self.client.post('/api/v1/health-logs/blood-pressure/', {
            "systolic_mmHg": 185,
            "diastolic_mmHg": 85,
            "pulse_bpm": 76,
        })
        assert r1.status_code == 201
        assert r1.data["is_crisis"] is True
        assert r1.data["bp_stage"] == "HYPERTENSIVE_CRISIS"

        # Case 2: Systolic normal, Diastolic > 120 (130/125) -> CRISIS
        r2 = self.client.post('/api/v1/health-logs/blood-pressure/', {
            "systolic_mmHg": 130,
            "diastolic_mmHg": 125,
            "pulse_bpm": 80,
        })
        assert r2.status_code == 201
        assert r2.data["is_crisis"] is True
        assert r2.data["bp_stage"] == "HYPERTENSIVE_CRISIS"

        # Case 3: Both elevated (190/130) -> CRISIS
        r3 = self.client.post('/api/v1/health-logs/blood-pressure/', {
            "systolic_mmHg": 190,
            "diastolic_mmHg": 130,
            "pulse_bpm": 88,
        })
        assert r3.status_code == 201
        assert r3.data["is_crisis"] is True

        # Case 4: Below threshold (179/119) -> NOT crisis
        r4 = self.client.post('/api/v1/health-logs/blood-pressure/', {
            "systolic_mmHg": 179,
            "diastolic_mmHg": 119,
            "pulse_bpm": 74,
        })
        assert r4.status_code == 201
        assert r4.data["is_crisis"] is False

    def test_hard_limits_physiological_validation(self):
        """Typo guardrails reject biologically impossible vitals with 400 Bad Request."""
        # Glucose impossible negative or extreme (< 0.5 or > 60)
        r_glu_low = self.client.post('/api/v1/health-logs/blood-glucose/', {"glucose_value_mmol": "0.2", "reading_type": "FASTING"})
        assert r_glu_low.status_code == 400

        r_glu_high = self.client.post('/api/v1/health-logs/blood-glucose/', {"glucose_value_mmol": "75.0", "reading_type": "FASTING"})
        assert r_glu_high.status_code == 400

        # BP impossible (< 40 or > 300 systolic)
        r_bp_low = self.client.post('/api/v1/health-logs/blood-pressure/', {"systolic_mmHg": 20, "diastolic_mmHg": 60, "pulse_bpm": 70})
        assert r_bp_low.status_code == 400

        r_bp_high = self.client.post('/api/v1/health-logs/blood-pressure/', {"systolic_mmHg": 350, "diastolic_mmHg": 80, "pulse_bpm": 70})
        assert r_bp_high.status_code == 400

        # Weight impossible (< 1.0 or > 500)
        r_wt = self.client.post('/api/v1/health-logs/weight/', {"weight_kg": "600.0"})
        assert r_wt.status_code == 400

    def test_danger_alert_acknowledgment_lifecycle(self):
        """Patient can acknowledge danger alert with resolution notes."""
        # Create alert directly
        alert = DangerAlert.objects.create(
            patient=self.patient_profile,
            alert_type=DangerAlert.AlertType.HYPOGLYCEMIA,
            trigger_value="2.8 mmol/L",
            instruction_text="Consume 15g fast acting sugar immediately.",
        )
        assert alert.is_acknowledged is False

        # Acknowledge alert
        ack_res = self.client.post(f'/api/v1/health-logs/danger-alerts/{alert.id}/acknowledge/')
        assert ack_res.status_code == 200
        assert ack_res.data["success"] is True

        alert.refresh_from_db()
        assert alert.is_acknowledged is True

    def test_weight_log_with_height_and_bmi_calculation(self):
        """Logging weight with optional height calculates BMI and persists to patient profile."""
        res = self.client.post('/api/v1/health-logs/weight/', {
            "weight_kg": "70.0",
            "height_cm": "175.0",
        })
        assert res.status_code == 201
        assert float(res.data["weight_kg"]) == 70.0
        assert float(res.data["calculated_bmi"]) == 22.9
        assert res.data["bmi_category"] == "Normal"

        self.patient_profile.refresh_from_db()
        assert float(self.patient_profile.height_cm) == 175.0
