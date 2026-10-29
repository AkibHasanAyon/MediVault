from rest_framework import status, views, permissions
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import User
from .serializers import (
    UserRegistrationSerializer,
    OTPVerificationSerializer,
    ResendOTPSerializer,
    UserSerializer,
)
from .services.otp_service import OTPService
from apps.notifications.services import MessagingService

class RegisterView(views.APIView):
    """
    Registers a new user (Patient, Doctor, or Clinic Assistant).
    Generates a 6-digit cryptographic OTP and dispatches it via
    the active messaging channel (SMTP Email in development, SMS in production).
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=UserRegistrationSerializer,
        responses={
            201: OpenApiResponse(description="User registered successfully. OTP dispatched."),
            400: OpenApiResponse(description="Validation error in phone number or fields."),
        }
    )
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = serializer.save()

        # Generate OTP
        otp_code = OTPService.generate_otp(user.phone_number)

        # Dispatch OTP via MessagingService (Email in dev/prototype, SMS in live prod)
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
    Verifies the submitted 6-digit OTP code against the salted cache hash.
    Marks user as verified and returns JWT Access & Refresh token pair.
    """
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=OTPVerificationSerializer,
        responses={
            200: OpenApiResponse(description="Identity verified. JWT tokens issued."),
            400: OpenApiResponse(description="Invalid or expired OTP code."),
            404: OpenApiResponse(description="User with specified phone number not found."),
        }
    )
    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        phone_number = serializer.validated_data['phone_number']
        otp_code = serializer.validated_data['otp_code']

        is_valid, msg = OTPService.verify_otp(phone_number, otp_code)
        if not is_valid:
            return Response(
                {"success": False, "message": msg},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response(
                {"success": False, "message": "User not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Mark user verified
        user.is_phone_verified = True
        if user.email:
            user.is_email_verified = True
        user.save(update_fields=['is_phone_verified', 'is_email_verified'])

        # Issue JWT pair
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "success": True,
                "message": "Phone number successfully verified.",
                "data": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": UserSerializer(user).data
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

    @extend_schema(
        request=ResendOTPSerializer,
        responses={
            200: OpenApiResponse(description="Fresh OTP dispatched."),
            404: OpenApiResponse(description="User not found."),
        }
    )
    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        phone_number = serializer.validated_data['phone_number']
        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            return Response(
                {"success": False, "message": "No account registered with this phone number."},
                status=status.HTTP_404_NOT_FOUND
            )

        otp_code = OTPService.generate_otp(user.phone_number)
        MessagingService.send_otp(
            recipient_phone=user.phone_number,
            recipient_email=user.email,
            otp_code=otp_code,
            user_name=user.full_name
        )

        return Response(
            {
                "success": True,
                "message": "Fresh 6-digit verification code dispatched.",
                "data": {
                    "resend_countdown_seconds": 60,
                    "channel": MessagingService.get_backend()
                }
            },
            status=status.HTTP_200_OK
        )


class UserProfileView(views.APIView):
    """Returns the authenticated user's profile details."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response({"success": True, "data": serializer.data})

