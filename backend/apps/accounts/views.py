import random
from rest_framework import status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse
from django.conf import settings

from .models import User
from .serializers import (
    UserRegistrationSerializer,
    OTPVerificationSerializer,
    ResendOTPSerializer,
    UserSerializer,
    validate_bangladeshi_phone,
)
from .services.otp_service import OTPService
from apps.notifications.services import MessagingService


class RegisterView(views.APIView):
    """
    Registers a new user (Patient, Doctor, or Clinic Assistant).
    Supports email-first onboarding as well as phone registration.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        data = request.data.copy()

        if data.get('email'):
            data['email'] = data['email'].strip().lower()

        # If email provided but no phone, auto-generate valid placeholder BD phone
        if data.get('email') and not data.get('phone_number'):
            while True:
                candidate = f"+88017{random.randint(10000000, 99999999)}"
                if not User.objects.filter(phone_number=candidate).exists():
                    data['phone_number'] = candidate
                    break

        # If no password provided, supply a compliant temporary password
        if not data.get('password'):
            data['password'] = f"MediVault_{random.randint(100000, 999999)}#Pass"

        serializer = UserRegistrationSerializer(data=data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors, "message": "Validation failed."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.save()

        # Update profile with real given information — NO dummy data
        if user.role == User.Role.DOCTOR:
            from apps.doctors.models import DoctorProfile
            doctor_profile, _ = DoctorProfile.objects.get_or_create(user=user)
            bmdc = request.data.get('bmdc_number', '').strip() or request.data.get('bmdc_registration_number', '').strip()
            specialty = request.data.get('specialty', '').strip() or request.data.get('primary_specialty', '').strip()
            qualifications = request.data.get('degrees_qualifications', '').strip() or request.data.get('qualifications', '').strip()
            if bmdc:
                doctor_profile.bmdc_registration_number = bmdc
            if specialty:
                doctor_profile.primary_specialty = specialty
            if qualifications:
                doctor_profile.degrees_qualifications = qualifications
            doctor_profile.save()

        elif user.role == User.Role.PATIENT:
            from apps.patients.models import PatientProfile
            patient_profile, _ = PatientProfile.objects.get_or_create(user=user)
            gender = request.data.get('gender')
            dob = request.data.get('date_of_birth')
            blood_group = request.data.get('blood_group')
            emergency_phone = request.data.get('emergency_contact_phone')
            allergies = request.data.get('known_allergies')

            if gender and gender in PatientProfile.Gender.values:
                patient_profile.gender = gender
            if dob:
                patient_profile.date_of_birth = dob
            if blood_group and blood_group in PatientProfile.BloodGroup.values:
                patient_profile.blood_group = blood_group
            if emergency_phone:
                patient_profile.emergency_contact_phone = emergency_phone
            if allergies:
                patient_profile.known_allergies = allergies
            patient_profile.save()

        elif user.role == User.Role.ASSISTANT:
            from apps.clinics.models import Clinic, ClinicAssistantProfile
            clinic_id = request.data.get('clinic_id')
            clinic = Clinic.objects.filter(id=clinic_id).first() if clinic_id else Clinic.objects.first()
            if clinic:
                ClinicAssistantProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'clinic': clinic,
                        'desk_serial': request.data.get('desk_serial', 'Desk-1'),
                    }
                )

        identifier = user.email or user.phone_number
        secondary = user.phone_number if identifier == user.email else user.email
        otp_code = OTPService.generate_otp(identifier, secondary_identifier=secondary)

        MessagingService.send_otp(
            recipient_phone=user.phone_number,
            recipient_email=user.email,
            otp_code=otp_code,
            user_name=user.full_name
        )

        delivery_channel = MessagingService.get_backend()
        message = (
            f"User registered successfully. Verification OTP dispatched via {delivery_channel.upper()}."
        )

        return Response(
            {
                "success": True,
                "message": message,
                "data": {
                    "user_id": str(user.id),
                    "phone_number": user.phone_number,
                    "email": user.email,
                    "role": user.role,
                    "is_phone_verified": user.is_phone_verified,
                    "otp_delivery_channel": delivery_channel,
                }
            },
            status=status.HTTP_201_CREATED
        )


class VerifyPhoneView(views.APIView):
    """
    Verifies the submitted 6-digit OTP code against Email or Phone.
    Marks user as verified and returns JWT Access & Refresh token pair.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        raw_phone = request.data.get('phone_number', '').strip()
        otp_code = request.data.get('otp_code', '').strip()

        if not otp_code:
            return Response(
                {"success": False, "message": "OTP code is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        identifier = email if email else raw_phone
        if not identifier:
            return Response(
                {"success": False, "message": "Email or phone number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Direct OTP verification
        is_valid, msg = OTPService.verify_otp(identifier, otp_code)

        # 2. Dual fallback lookup (email <-> phone) only if primary identifier had no active OTP
        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
            if not is_valid and ("not requested" in msg or "expired" in msg) and user and user.phone_number:
                fallback_valid, fallback_msg = OTPService.verify_otp(user.phone_number, otp_code)
                if fallback_valid:
                    is_valid, msg = fallback_valid, fallback_msg
        elif raw_phone:
            try:
                phone_num = validate_bangladeshi_phone(raw_phone)
                user = User.objects.filter(phone_number=phone_num).first()
                if not is_valid and ("not requested" in msg or "expired" in msg) and user and user.email:
                    fallback_valid, fallback_msg = OTPService.verify_otp(user.email, otp_code)
                    if fallback_valid:
                        is_valid, msg = fallback_valid, fallback_msg
            except Exception:
                pass

        if not is_valid:
            return Response(
                {"success": False, "message": msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user:
            return Response(
                {"success": False, "message": "User account not found. Please register."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Mark user verified
        user.is_phone_verified = True
        user.is_email_verified = True
        user.save(update_fields=['is_phone_verified', 'is_email_verified'])

        # Issue JWT pair
        refresh = RefreshToken.for_user(user)
        user_data = UserSerializer(user).data
        if hasattr(user, 'patient_profile'):
            user_data['patient_profile_id'] = str(user.patient_profile.id)
        if hasattr(user, 'doctor_profile'):
            user_data['doctor_profile_id'] = str(user.doctor_profile.id)
            user_data['bmdc_number'] = getattr(user.doctor_profile, 'bmdc_number', '')
        if hasattr(user, 'assistant_profile'):
            user_data['assistant_profile_id'] = str(user.assistant_profile.id)
            if user.assistant_profile.clinic:
                user_data['clinic_id'] = str(user.assistant_profile.clinic.id)

        tokens_data = {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": user_data
        }

        return Response(
            {
                "success": True,
                "message": "Identity successfully verified via email.",
                "data": tokens_data,
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data
            },
            status=status.HTTP_200_OK
        )


class RequestOTPView(views.APIView):
    """
    Dispatches a 6-digit OTP code to the registered user's Email or Phone number.
    Rejects unregistered users with a friendly 404 prompting them to register.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        raw_phone = request.data.get('phone_number', '').strip()

        if not email and not raw_phone:
            return Response(
                {"success": False, "message": "Email or phone number is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
        elif raw_phone:
            try:
                formatted_phone = validate_bangladeshi_phone(raw_phone)
                user = User.objects.filter(phone_number=formatted_phone).first()
            except Exception:
                pass

        if not user:
            return Response(
                {
                    "success": False,
                    "code": "USER_NOT_FOUND",
                    "message": f"No account registered with {email or raw_phone}. Please click Create Account (নিবন্ধন করুন) to register.",
                },
                status=status.HTTP_404_NOT_FOUND
            )

        identifier = user.email or user.phone_number
        secondary = user.phone_number if identifier == user.email else user.email
        otp_code = OTPService.generate_otp(identifier, secondary_identifier=secondary)

        MessagingService.send_otp(
            recipient_phone=user.phone_number,
            recipient_email=user.email,
            otp_code=otp_code,
            user_name=user.full_name
        )

        delivery_channel = MessagingService.get_backend()
        return Response(
            {
                "success": True,
                "message": f"Verification code dispatched to {user.email or user.phone_number}.",
                "data": {
                    "email": user.email,
                    "phone_number": user.phone_number,
                    "channel": delivery_channel
                }
            },
            status=status.HTTP_200_OK
        )



class ResendOTPView(views.APIView):
    """
    Resends a fresh 6-digit OTP code to the registered user.
    Enforces rate limits and 60-second cooldown period.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        raw_phone = request.data.get('phone_number', '').strip()

        user = None
        if email:
            user = User.objects.filter(email__iexact=email).first()
        elif raw_phone:
            try:
                formatted_phone = validate_bangladeshi_phone(raw_phone)
                user = User.objects.filter(phone_number=formatted_phone).first()
            except Exception:
                pass

        if not user:
            return Response(
                {"success": False, "message": "No account registered with this identifier."},
                status=status.HTTP_404_NOT_FOUND
            )

        identifier = user.email or user.phone_number
        secondary = user.phone_number if identifier == user.email else user.email
        otp_code = OTPService.generate_otp(identifier, secondary_identifier=secondary)

        MessagingService.send_otp(
            recipient_phone=user.phone_number,
            recipient_email=user.email,
            otp_code=otp_code,
            user_name=user.full_name
        )

        return Response(
            {
                "success": True,
                "message": f"Fresh 6-digit verification code dispatched to {user.email or user.phone_number}.",
                "data": {
                    "resend_countdown_seconds": 60,
                    "channel": MessagingService.get_backend()
                }
            },
            status=status.HTTP_200_OK
        )


class LogoutView(views.APIView):
    """Blacklists the refresh token upon user logout."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                pass
        return Response({"success": True, "message": "Logged out successfully."}, status=status.HTTP_200_OK)


class UserProfileView(views.APIView):
    """Returns the authenticated user's profile details."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        user = request.user
        data = UserSerializer(user).data
        if hasattr(user, 'patient_profile'):
            data['patient_profile_id'] = str(user.patient_profile.id)
        if hasattr(user, 'doctor_profile'):
            data['doctor_profile_id'] = str(user.doctor_profile.id)
            data['bmdc_number'] = getattr(user.doctor_profile, 'bmdc_number', '')
        if hasattr(user, 'assistant_profile'):
            data['assistant_profile_id'] = str(user.assistant_profile.id)
            if user.assistant_profile.clinic:
                data['clinic_id'] = str(user.assistant_profile.clinic.id)
        return Response({"success": True, "data": data, **data})

