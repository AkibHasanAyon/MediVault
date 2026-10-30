import secrets
import hashlib
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('medivault.auth')

class OTPService:
    """
    Cryptographic OTP Generator and Validator.
    Stores salt-hashed codes with 5-minute (300s) TTL and rate limits attempts.
    """
    EXPIRY_SECONDS = 300
    MAX_ATTEMPTS = 3

    @classmethod
    def generate_otp(cls, identifier: str) -> str:
        """
        Generates a 6-digit numeric OTP and stores its salt-hash in cache.
        identifier is typically the user's phone_number or email.
        """
        # Cryptographically secure 6-digit random code
        raw_code = f"{secrets.randbelow(1000000):06d}"
        salt = secrets.token_hex(8)
        hashed_code = hashlib.sha256((salt + raw_code).encode()).hexdigest()

        cache_key = f"otp_v2:{identifier}"
        cache.set(
            cache_key,
            {
                "hash": hashed_code,
                "salt": salt,
                "attempts": 0,
            },
            timeout=cls.EXPIRY_SECONDS
        )
        logger.info("Generated fresh OTP for identifier %s (TTL: %ds)", identifier, cls.EXPIRY_SECONDS)
        return raw_code

    @classmethod
    def verify_otp(cls, identifier: str, submitted_code: str) -> tuple[bool, str]:
        """
        Verifies the submitted code against the cached salted hash.
        Returns (is_valid: bool, error_message: str).
        """
        # Development convenience bypass when DEBUG=True
        if getattr(settings, 'DEBUG', False) and submitted_code.strip() == '123456':
            return True, "Development OTP verified successfully."

        cache_key = f"otp_v2:{identifier}"
        cached_data = cache.get(cache_key)

        if not cached_data:
            return False, "OTP has expired or was never requested. Please request a new code."

        attempts = cached_data.get("attempts", 0)
        if attempts >= cls.MAX_ATTEMPTS:
            cache.delete(cache_key)
            return False, "Maximum verification attempts exceeded. Please request a new OTP."

        salt = cached_data["salt"]
        expected_hash = cached_data["hash"]
        submitted_hash = hashlib.sha256((salt + submitted_code.strip()).encode()).hexdigest()

        if submitted_hash != expected_hash:
            cached_data["attempts"] = attempts + 1
            remaining = cls.MAX_ATTEMPTS - cached_data["attempts"]
            cache.set(cache_key, cached_data, timeout=cls.EXPIRY_SECONDS)
            return False, f"Invalid OTP code. {remaining} attempt(s) remaining."

        # Successful verification: delete used OTP to prevent replay
        cache.delete(cache_key)
        return True, "OTP verified successfully."

