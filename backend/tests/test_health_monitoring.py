import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import time, timedelta
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.patients.models import PatientProfile, FamilyMember
from apps.health_logs.models import (
    BloodGlucoseLog,
    BloodPressureLog,
    WeightLog,
    SymptomNote,
    DangerAlert,
)
from apps.medications.models import (
    Medication,
    MedicationReminder,
    MedicationAdherence,
)
from apps.medications.tasks import dispatch_scheduled_medication_reminders

@pytest.fixture
def api_client():
    return APIClient()

@pytest.fixture
def patient_user():
    user = User.objects.create_user(
        phone_number="+8801730000001",
        email="patient.health@example.com",
        password="secretpassword",
        full_name="Abdur Rahim"
    )
    # Ensure profile height is set for BMI calculation
    profile = user.patient_profile
    profile.height_cm = Decimal('175.0')
    profile.emergency_contact_phone = "+8801730000099"
    profile.save()
    return user

@pytest.mark.django_db
class TestPhase4HealthMonitoringAndDangerAlerts:

    def test_glucose_logging_and_mgdl_conversion(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        # 1. Standard mmol/L log
        payload1 = {
            "glucose_value_mmol": "5.6",
            "reading_type": "FASTING",
            "notes": "Morning check before tea"
        }
        res1 = api_client.post('/api/v1/health-logs/blood-glucose/', data=payload1)
        assert res1.status_code == 201
        assert res1.data["glucose_value_mmol"] == "5.6"

        # 2. mg/dL auto-conversion (180 mg/dL / 18.0182 ≈ 10.0 mmol/L)
        payload2 = {
            "glucose_value_mgdl": "180.0",
            "reading_type": "POST_MEAL"
        }
        res2 = api_client.post('/api/v1/health-logs/blood-glucose/', data=payload2)
        assert res2.status_code == 201
        assert Decimal(res2.data["glucose_value_mmol"]) == Decimal('10.0')

        # 3. Physiological limit rejection: 99 mmol/L should return 400
        payload_invalid = {
            "glucose_value_mmol": "99.0",
            "reading_type": "RANDOM"
        }
        res_invalid = api_client.post('/api/v1/health-logs/blood-glucose/', data=payload_invalid)
        assert res_invalid.status_code == 400
        assert "glucose_value_mmol" in res_invalid.data

    def test_blood_pressure_logging_and_staging(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        # 1. Normal BP
        res_norm = api_client.post('/api/v1/health-logs/blood-pressure/', data={
            "systolic_mmHg": 118,
            "diastolic_mmHg": 78,
            "pulse_bpm": 72
        })
        assert res_norm.status_code == 201
        assert res_norm.data["bp_stage"] == "NORMAL"
        assert res_norm.data["is_crisis"] is False

        # 2. Stage 2 Hypertension
        res_s2 = api_client.post('/api/v1/health-logs/blood-pressure/', data={
            "systolic_mmHg": 155,
            "diastolic_mmHg": 95,
            "pulse_bpm": 80
        })
        assert res_s2.status_code == 201
        assert res_s2.data["bp_stage"] == "STAGE_2_HYPERTENSION"

        # 3. Reject physiologically impossible values (systolic 350)
        res_err = api_client.post('/api/v1/health-logs/blood-pressure/', data={
            "systolic_mmHg": 350,
            "diastolic_mmHg": 90
        })
        assert res_err.status_code == 400

    def test_weight_logging_and_bmi_computation(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        # Patient height is 175cm (1.75m). Weight: 70 kg -> BMI: 70 / (1.75^2) ≈ 22.9
        res = api_client.post('/api/v1/health-logs/weight/', data={
            "weight_kg": "70.0"
        })
        assert res.status_code == 201
        assert Decimal(res.data["calculated_bmi"]) == Decimal('22.9')

    def test_symptom_notes_logging(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        res = api_client.post('/api/v1/health-logs/symptoms/', data={
            "symptom_tags": "Headache, Dizziness, Fatigue",
            "severity": "MODERATE",
            "notes": "Started after walking in hot weather"
        })
        assert res.status_code == 201
        assert res.data["severity"] == "MODERATE"
        assert "Headache" in res.data["symptom_tags"]

    def test_danger_alert_hypoglycemia_trigger(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        # Glucose 3.1 mmol/L (< 3.9 threshold)
        res = api_client.post('/api/v1/health-logs/blood-glucose/', data={
            "glucose_value_mmol": "3.1",
            "reading_type": "FASTING"
        })
        assert res.status_code == 201
        assert res.data["is_danger"] is True

        # Verify DangerAlert was auto-created
        alert = DangerAlert.objects.filter(patient=patient_user.patient_profile).first()
        assert alert is not None
        assert alert.alert_type == DangerAlert.AlertType.HYPOGLYCEMIA
        assert "15g fast-acting sugar" in alert.instruction_text
        assert alert.notification_dispatched is True

    def test_danger_alert_hypertensive_crisis_or_logic(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        # Systolic 185, Diastolic 85 (Systolic > 180 triggers Hypertensive Crisis)
        res = api_client.post('/api/v1/health-logs/blood-pressure/', data={
            "systolic_mmHg": 185,
            "diastolic_mmHg": 85,
            "pulse_bpm": 88
        })
        assert res.status_code == 201
        assert res.data["is_crisis"] is True
        assert res.data["bp_stage"] == "HYPERTENSIVE_CRISIS"

        # Verify Hypertensive Crisis alert created
        crisis_alert = DangerAlert.objects.filter(
            patient=patient_user.patient_profile,
            alert_type=DangerAlert.AlertType.HYPERTENSIVE_CRISIS
        ).first()
        assert crisis_alert is not None
        assert "999" in crisis_alert.instruction_text
        assert crisis_alert.notification_dispatched is True

    def test_danger_alert_acknowledgment_flow(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        alert = DangerAlert.objects.create(
            patient=patient_user.patient_profile,
            alert_type=DangerAlert.AlertType.HYPERGLYCEMIA,
            trigger_value="17.5 mmol/L",
            instruction_text="Critical high blood glucose."
        )
        assert alert.is_acknowledged is False

        # Patient acknowledges the alert
        res = api_client.post(f'/api/v1/health-logs/danger-alerts/{alert.id}/acknowledge/')
        assert res.status_code == 200
        assert res.data["success"] is True

        alert.refresh_from_db()
        assert alert.is_acknowledged is True

    def test_vitals_summary_dashboard(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        # Log some vitals
        api_client.post('/api/v1/health-logs/blood-glucose/', data={"glucose_value_mmol": "6.0"})
        api_client.post('/api/v1/health-logs/blood-pressure/', data={"systolic_mmHg": 125, "diastolic_mmHg": 80})

        res = api_client.get('/api/v1/health-logs/summary/')
        assert res.status_code == 200
        data = res.data["data"]
        assert data["latest_glucose"] is not None
        assert data["latest_bp"] is not None

    def test_medication_dosage_pattern_schedule_generation(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        # Create active medication with pattern 1+0+1
        res = api_client.post('/api/v1/medications/', data={
            "name": "Nexum",
            "generic_name": "Esomeprazole",
            "strength": "20mg",
            "dosage_pattern": "1+0+1",
            "start_date": "2026-10-30",
            "refill_remaining_doses": 30
        })
        assert res.status_code == 201
        med_id = res.data["id"]

        med = Medication.objects.get(id=med_id)
        # Reminders should have been auto-created (Morning + Night)
        reminders = med.reminders.all()
        assert reminders.count() == 2
        labels = [r.label for r in reminders]
        assert "Morning Dose" in labels
        assert "Night Dose" in labels

    def test_medication_adherence_logging_and_safeguards(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        med = Medication.objects.create(
            patient=patient_user.patient_profile,
            name="Metfo",
            generic_name="Metformin",
            strength="500mg",
            dosage_pattern="1+0+0",
            start_date="2026-10-30",
            refill_remaining_doses=30
        )
        reminder = MedicationReminder.objects.create(
            medication=med,
            reminder_time=time(8, 0),
            label="Morning Dose"
        )

        # 1. Log TAKEN: refill count decrements from 30 to 29
        res_taken = api_client.post(f'/api/v1/medications/{med.id}/record-adherence/', data={
            "action": "TAKEN",
            "reminder_id": str(reminder.id)
        })
        assert res_taken.status_code == 201
        assert res_taken.data["refill_remaining_doses"] == 29
        med.refresh_from_db()
        assert med.refill_remaining_doses == 29

        # 2. Log SKIPPED: returns clinical safeguard warning (Never take double dose)
        res_skipped = api_client.post(f'/api/v1/medications/{med.id}/record-adherence/', data={
            "action": "SKIPPED",
            "reminder_id": str(reminder.id),
            "skip_reason": "Forgot during travel"
        })
        assert res_skipped.status_code == 201
        assert "Never take a double" in res_skipped.data["clinical_safeguard"]

    def test_medication_today_schedule_and_adherence_analytics(self, api_client, patient_user):
        api_client.force_authenticate(user=patient_user)

        med = Medication.objects.create(
            patient=patient_user.patient_profile,
            name="Seclo",
            strength="20mg",
            dosage_pattern="1+0+0",
            start_date=timezone.localdate(),
            refill_remaining_doses=14
        )
        reminder = MedicationReminder.objects.create(
            medication=med,
            reminder_time=time(8, 0),
            label="Morning Dose"
        )

        # GET /api/v1/medications/today/ -> Initially PENDING
        res_today = api_client.get('/api/v1/medications/today/')
        assert res_today.status_code == 200
        assert res_today.data["total_doses"] >= 1
        doses = res_today.data["doses"]
        target_dose = next(d for d in doses if d["medication_id"] == str(med.id))
        assert target_dose["status"] == "PENDING"

        # Record TAKEN
        api_client.post(f'/api/v1/medications/{med.id}/record-adherence/', data={
            "action": "TAKEN",
            "reminder_id": str(reminder.id)
        })

        # GET /api/v1/medications/today/ -> Now TAKEN
        res_today_after = api_client.get('/api/v1/medications/today/')
        target_dose_after = next(d for d in res_today_after.data["doses"] if d["medication_id"] == str(med.id))
        assert target_dose_after["status"] == "TAKEN"

        # GET /api/v1/medications/adherence-stats/
        res_stats = api_client.get('/api/v1/medications/adherence-stats/')
        assert res_stats.status_code == 200
        assert res_stats.data["data"]["overall_adherence_percentage"] == 100.0

    def test_celery_beat_reminder_dispatcher(self, patient_user):
        now_time = timezone.localtime().time()
        med = Medication.objects.create(
            patient=patient_user.patient_profile,
            name="Rosuvas",
            strength="10mg",
            dosage_pattern="0+0+1",
            start_date=timezone.localdate(),
            refill_remaining_doses=30
        )
        MedicationReminder.objects.create(
            medication=med,
            reminder_time=now_time,
            label="Night Dose",
            is_enabled=True
        )

        # Execute Celery Beat task
        dispatched_count = dispatch_scheduled_medication_reminders()
        assert dispatched_count >= 1
