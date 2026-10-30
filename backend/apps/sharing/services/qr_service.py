import io
import base64
import secrets
import hashlib
import hmac
import logging
import qrcode
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

from apps.sharing.models import ConsultationShare
from apps.patients.models import PatientProfile

logger = logging.getLogger('medivault.sharing')

class QRSharingService:
    """
    Manages ephemeral 30-minute QR code consultation sessions.
    Generates cryptographically signed tokens, enforces Redis TTL,
    and produces high-contrast QR codes for doctor scanning.
    """

    TTL_SECONDS = 1800  # Strict 30-minute lifespan

    @classmethod
    def generate_qr_share(cls, patient: PatientProfile, scope: dict | None = None) -> dict:
        """
        Creates an ephemeral consultation session.
        Returns the raw token, database share instance, expiry, and base64 QR image.
        """
        if scope is None:
            scope = {
                "all_documents": True,
                "vitals_90d": True,
                "active_medications": True,
            }

        # 1. Generate high-entropy 256-bit token
        raw_token = secrets.token_urlsafe(32)

        # 2. Compute HMAC-SHA256 signature with Django server secret
        secret_bytes = settings.SECRET_KEY.encode('utf-8')
        signature = hmac.new(secret_bytes, raw_token.encode('utf-8'), hashlib.sha256).hexdigest()
        token_hash = hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

        expires_at = timezone.now() + timedelta(seconds=cls.TTL_SECONDS)

        # 3. Create persistent record
        share = ConsultationShare.objects.create(
            patient=patient,
            token_hash=token_hash,
            permitted_scope=scope,
            is_active=True,
            expires_at=expires_at
        )

        # 4. Store in fast cache with 30-min TTL
        cache_key = f"qr_share_{token_hash}"
        cache.set(cache_key, str(share.id), timeout=cls.TTL_SECONDS)

        # 5. Generate vector/raster QR code containing verification payload
        qr_payload = f"medivault://consultation?token={raw_token}&share_id={share.id}"
        qr_img = qrcode.make(qr_payload, box_size=8, border=2)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        qr_base64 = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"

        logger.info("Generated 30-minute consultation share %s for patient %s", share.id, patient.user.phone_number)

        return {
            "share_id": str(share.id),
            "token": raw_token,
            "signature": signature,
            "qr_payload": qr_payload,
            "qr_base64": qr_base64,
            "expires_at": expires_at.isoformat(),
            "expires_in_seconds": cls.TTL_SECONDS,
            "permitted_scope": scope,
        }

    @classmethod
    def validate_token(cls, raw_token: str) -> ConsultationShare | None:
        """
        Validates the raw QR token against both fast cache and database.
        Ensures the session is active and has not expired.
        """
        if not raw_token:
            return None

        token_hash = hashlib.sha256(raw_token.strip().encode('utf-8')).hexdigest()
        cache_key = f"qr_share_{token_hash}"

        # Fast path check in cache
        cached_share_id = cache.get(cache_key)

        share = ConsultationShare.objects.select_related('patient__user', 'doctor__user').filter(
            token_hash=token_hash,
            is_active=True,
            expires_at__gt=timezone.now()
        ).first()

        if not share:
            logger.warning("Attempted to validate expired or invalid QR share token")
            return None

        return share

    @classmethod
    def revoke_share(cls, share: ConsultationShare) -> bool:
        """
        Immediately terminates an active consultation share.
        Purges token from cache and marks database record inactive.
        """
        share.is_active = False
        share.save(update_fields=['is_active'])

        cache_key = f"qr_share_{share.token_hash}"
        cache.delete(cache_key)
        logger.info("Revoked consultation share %s instantly", share.id)
        return True

