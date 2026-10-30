import pytest
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.accounts.services.otp_service import OTPService

@pytest.fixture
def api_client():
    return APIClient()

@pytest.mark.django_db
class TestAuthenticationEndpoints:

    def test_user_registration_success(self, api_client):
        payload = {
            "phone_number": "01712345678",
            "email": "test.patient@example.com",
            "password": "StrongPassword#2026",
            "full_name": "Rahim Ahmed",
            "role": "PATIENT",
            "preferred_language": "bn"
        }
        response = api_client.post('/api/v1/auth/register/', data=payload, format='json')
        assert response.status_code == 201
        assert response.data["success"] is True
        assert response.data["data"]["phone_number"] == "+8801712345678"
        assert response.data["data"]["is_phone_verified"] is False
        assert User.objects.filter(phone_number="+8801712345678").exists()

    def test_registration_duplicate_phone_rejected(self, api_client):
        User.objects.create_user(phone_number="+8801712345678", password="pwd", full_name="User 1")
        payload = {
            "phone_number": "01712345678",
            "password": "StrongPassword#2026",
            "full_name": "User 2"
        }
        response = api_client.post('/api/v1/auth/register/', data=payload, format='json')
        assert response.status_code == 400
        assert "phone_number" in response.data["errors"]

    def test_registration_invalid_phone_rejected(self, api_client):
        payload = {
            "phone_number": "12345",
            "password": "StrongPassword#2026",
            "full_name": "User Invalid"
        }
        response = api_client.post('/api/v1/auth/register/', data=payload, format='json')
        assert response.status_code == 400

    def test_otp_verification_flow(self, api_client):
        phone = "+8801812345678"
        user = User.objects.create_user(phone_number=phone, password="Password123!", full_name="Test User")
        
        # Generate known OTP
        otp_code = OTPService.generate_otp(phone)

        # Test with wrong OTP
        wrong_response = api_client.post('/api/v1/auth/verify-phone/', data={
            "phone_number": phone,
            "otp_code": "000000"
        }, format='json')
        assert wrong_response.status_code == 400
        assert "Invalid OTP" in wrong_response.data["message"]

        # Test with correct OTP
        correct_response = api_client.post('/api/v1/auth/verify-phone/', data={
            "phone_number": phone,
            "otp_code": otp_code
        }, format='json')
        assert correct_response.status_code == 200
        assert "access" in correct_response.data["data"]
        assert "refresh" in correct_response.data["data"]

        user.refresh_from_db()
        assert user.is_phone_verified is True

    def test_user_profile_requires_jwt_auth(self, api_client):
        phone = "+8801912345678"
        user = User.objects.create_user(phone_number=phone, password="Password123!", full_name="Profile User")
        
        # Unauthenticated request
        res_unauth = api_client.get('/api/v1/auth/me/')
        assert res_unauth.status_code == 401

        # Authenticate via client
        api_client.force_authenticate(user=user)
        res_auth = api_client.get('/api/v1/auth/me/')
        assert res_auth.status_code == 200
        assert res_auth.data["data"]["full_name"] == "Profile User"


    def test_email_registration_and_real_profile_creation(self, api_client):
        """Registration uses given information and saves to PatientProfile without dummy data."""
        payload = {
            "email": "real.patient@example.com",
            "full_name": "Mustafizur Rahman",
            "role": "PATIENT",
            "gender": "MALE",
            "blood_group": "B+",
            "date_of_birth": "1992-05-14",
            "emergency_contact_phone": "+8801799887766",
        }
        res = api_client.post('/api/v1/auth/register/', data=payload, format='json')
        assert res.status_code == 201

        user = User.objects.get(email="real.patient@example.com")
        assert user.full_name == "Mustafizur Rahman"
        assert hasattr(user, 'patient_profile')
        profile = user.patient_profile
        assert profile.gender == "MALE"
        assert profile.blood_group == "B+"
        assert str(profile.date_of_birth) == "1992-05-14"
        assert profile.emergency_contact_phone == "+8801799887766"

    def test_otp_verification_rejects_default_123456(self, api_client):
        """Default bypass code '123456' is rejected when it doesn't match the generated OTP."""
        email = "test.otp.reject@example.com"
        user = User.objects.create_user(phone_number="+8801788776655", email=email, full_name="OTP User")

        real_code = OTPService.generate_otp(email)
        assert real_code != "123456"

        # Submitting 123456 must FAIL
        res_default = api_client.post('/api/v1/auth/otp/verify/', data={
            "email": email,
            "otp_code": "123456"
        }, format='json')
        assert res_default.status_code == 400
        assert "Invalid OTP" in res_default.data["message"]

        # Submitting real code must SUCCEED
        res_real = api_client.post('/api/v1/auth/otp/verify/', data={
            "email": email,
            "otp_code": real_code
        }, format='json')
        assert res_real.status_code == 200
        assert "access" in res_real.data["data"]
