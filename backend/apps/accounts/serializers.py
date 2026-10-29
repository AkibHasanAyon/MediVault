import re
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User

def validate_bangladeshi_phone(value: str) -> str:
    """Validates and formats Bangladesh phone numbers into E.164 (+8801XXXXXXXXX)."""
    cleaned = re.sub(r'[\s\-()]', '', value)
    if cleaned.startswith('01') and len(cleaned) == 11:
        cleaned = f"+88{cleaned}"
    elif cleaned.startswith('8801') and len(cleaned) == 13:
        cleaned = f"+{cleaned}"
    
    pattern = r'^\+8801[3-9]\d{8}$'
    if not re.match(pattern, cleaned):
        raise serializers.ValidationError(
            "Enter a valid Bangladesh mobile number (e.g. +8801712345678 or 01712345678)."
        )
    return cleaned


class UserSerializer(serializers.ModelSerializer):
    """Public serialization of user profile."""
    class Meta:
        model = User
        fields = (
            'id',
            'phone_number',
            'email',
            'full_name',
            'role',
            'preferred_language',
            'is_phone_verified',
            'is_email_verified',
            'created_at',
        )
        read_only_fields = ('id', 'is_phone_verified', 'is_email_verified', 'created_at')


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for initial user signup."""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    email = serializers.EmailField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = User
        fields = (
            'id',
            'phone_number',
            'email',
            'password',
            'full_name',
            'role',
            'preferred_language',
        )
        read_only_fields = ('id',)

    def validate_phone_number(self, value):
        formatted = validate_bangladeshi_phone(value)
        if User.objects.filter(phone_number=formatted).exists():
            raise serializers.ValidationError("An account with this phone number already exists.")
        return formatted

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("An account with this email address already exists.")
        return value or None

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class OTPVerificationSerializer(serializers.Serializer):
    """Serializer for submitting the 6-digit verification OTP."""
    phone_number = serializers.CharField(required=True)
    otp_code = serializers.CharField(min_length=6, max_length=6, required=True)

    def validate_phone_number(self, value):
        return validate_bangladeshi_phone(value)


class ResendOTPSerializer(serializers.Serializer):
    """Serializer for requesting a fresh OTP."""
    phone_number = serializers.CharField(required=True)

    def validate_phone_number(self, value):
        return validate_bangladeshi_phone(value)

