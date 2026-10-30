import secrets
import hashlib
import logging
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger('medivault.auth')

class OTPService:
    """
    Cryptographic OTP Generator and Validator.
    Persists tokens securely in the database with cache acceleration.
    Stores salt-hashed codes with 5-minute (300s) TTL and rate limits attempts.
    """
    EXPIRY_SECONDS = 300
    MAX_ATTEMPTS = 3

    @classmethod
    def _normalize(cls, identifier: str) -> str:
        """Normalizes email or phone number string."""
        return identifier.strip().lower() if identifier else ""

    @classmethod
    def generate_otp(cls, identifier: str, secondary_identifier: str | None = None) -> str:
        """
        Generates a 6-digit numeric OTP and stores its salt-hash in DB and cache.
        identifier is typically the user's phone_number or email.
        If secondary_identifier is provided (e.g. user has both email and phone),
        the exact same OTP is registered for both so either can verify.
        """
        raw_code = f"{secrets.randbelow(1000000):06d}"
        salt = secrets.token_hex(8)
        hashed_code = hashlib.sha256((salt + raw_code).encode()).hexdigest()
        expires_at = timezone.now() + timedelta(seconds=cls.EXPIRY_SECONDS)

        targets = set()
        norm_primary = cls._normalize(identifier)
        if norm_primary:
            targets.add(norm_primary)
        if secondary_identifier:
            norm_secondary = cls._normalize(secondary_identifier)
            if norm_secondary:
                targets.add(norm_secondary)

        from apps.accounts.models import OTPToken

        for target in targets:
            # Invalidate any previously unused active tokens for this identifier
            OTPToken.objects.filter(identifier=target, is_used=False).update(is_used=True)

            # Persist fresh token record
            OTPToken.objects.create(
                identifier=target,
                code_hash=hashed_code,
                salt=salt,
                attempts=0,
                expires_at=expires_at,
                is_used=False
            )

            # Also update cache
            cache_key = f"otp_v2:{target}"
            cache.set(
                cache_key,
                {
                    "hash": hashed_code,
                    "salt": salt,
                    "attempts": 0,
                },
                timeout=cls.EXPIRY_SECONDS
            )

        logger.info("Generated persistent OTP for identifier(s) %s (TTL: %ds)", list(targets), cls.EXPIRY_SECONDS)
        return raw_code

    @classmethod
    def verify_otp(cls, identifier: str, submitted_code: str) -> tuple[bool, str]:
        """
        Verifies the submitted code against the persistent salted hash.
        Returns (is_valid: bool, error_message: str).
        """
        code = submitted_code.strip() if submitted_code else ""
        if not code or len(code) != 6 or not code.isdigit():
            return False, "Please enter a valid 6-digit verification code."

        norm = cls._normalize(identifier)
        if not norm:
            return False, "Identifier is required."

        from apps.accounts.models import OTPToken

        # 1. Primary lookup: check persistent OTPToken model
        token = OTPToken.objects.filter(identifier=norm, is_used=False).order_by('-created_at').first()

        if token:
            # Check expiration
            if token.expires_at < timezone.now():
                token.is_used = True
                token.save(update_fields=['is_used'])
                return False, "Verification code has expired. Please request a new code."

            # Check attempt limit
            if token.attempts >= cls.MAX_ATTEMPTS:
                token.is_used = True
                token.save(update_fields=['is_used'])
                return False, "Maximum verification attempts exceeded. Please request a new code."

            # Verify cryptographic hash
            submitted_hash = hashlib.sha256((token.salt + code).encode()).hexdigest()
            if submitted_hash != token.code_hash:
                token.attempts += 1
                token.save(update_fields=['attempts'])
                remaining = cls.MAX_ATTEMPTS - token.attempts
                if remaining <= 0:
                    token.is_used = True
                    token.save(update_fields=['is_used'])
                    return False, "Maximum verification attempts exceeded. Please request a new code."
                return False, f"Invalid OTP code. {remaining} attempt(s) remaining."

            # Success: mark token used and clear cache
            token.is_used = True
            token.save(update_fields=['is_used'])
            cache.delete(f"otp_v2:{norm}")
            return True, "Verification successful."

        # 2. Fallback lookup: check cache
        cache_key = f"otp_v2:{norm}"
        cached_data = cache.get(cache_key)

        if not cached_data:
            return False, "Verification code has expired or was not requested. Please request a new code."

        attempts = cached_data.get("attempts", 0)
        if attempts >= cls.MAX_ATTEMPTS:
            cache.delete(cache_key)
            return False, "Maximum verification attempts exceeded. Please request a new code."

        salt = cached_data["salt"]
        expected_hash = cached_data["hash"]
        submitted_hash = hashlib.sha256((salt + code).encode()).hexdigest()

        if submitted_hash != expected_hash:
            cached_data["attempts"] = attempts + 1
            remaining = cls.MAX_ATTEMPTS - cached_data["attempts"]
            cache.set(cache_key, cached_data, timeout=cls.EXPIRY_SECONDS)
            return False, f"Invalid OTP code. {remaining} attempt(s) remaining."

        # Successful verification: delete used OTP to prevent replay
        cache.delete(cache_key)
        return True, "Verification successful."
