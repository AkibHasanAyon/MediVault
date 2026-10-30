import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedUUIDModel
from .managers import UserManager

class User(AbstractBaseUser, PermissionsMixin):
    """
    Primary user model for MediVault.
    Authenticates via phone_number (E.164 format e.g. +8801712345678)
    with optional email for notifications and recovery.
    """
    class Role(models.TextChoices):
        PATIENT = 'PATIENT', _('Patient')
        DOCTOR = 'DOCTOR', _('Doctor')
        ASSISTANT = 'ASSISTANT', _('Clinic Assistant')
        ADMIN = 'ADMIN', _('System Administrator')

    class Language(models.TextChoices):
        BANGLA = 'bn', _('Bangla')
        ENGLISH = 'en', _('English')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField(max_length=20, unique=True, db_index=True)
    email = models.EmailField(max_length=255, unique=True, null=True, blank=True, db_index=True)
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT, db_index=True)
    preferred_language = models.CharField(max_length=5, choices=Language.choices, default=Language.BANGLA)
    
    is_phone_verified = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.phone_number}) - {self.get_role_display()}"


class OTPToken(TimeStampedUUIDModel):
    """
    Cryptographic, persistent OTP verification model.
    Stores salt-hashed codes with expiration timestamps and rate limits attempts.
    """
    identifier = models.CharField(max_length=255, db_index=True, help_text="Normalized email or phone")
    code_hash = models.CharField(max_length=128)
    salt = models.CharField(max_length=64)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
    is_used = models.BooleanField(default=False, db_index=True)

    class Meta:
        verbose_name = _('OTP Token')
        verbose_name_plural = _('OTP Tokens')
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP for {self.identifier} (used={self.is_used})"


