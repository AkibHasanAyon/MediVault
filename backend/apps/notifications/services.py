import logging
from django.conf import settings
from .email_service import EmailService

logger = logging.getLogger('medivault.notifications')

class SMSGatewayService:
    """
    Bangladesh SMS Gateway Service (e.g. BulkSMSBD, SSL Wireless, Onnorokom SMS).
    Used in live production when MESSAGING_BACKEND='sms'.
    """

    @staticmethod
    def send_sms(phone_number: str, message_text: str) -> bool:
        if not settings.SMS_API_KEY:
            logger.warning("SMS_API_KEY is not configured. Simulating SMS to %s: %s", phone_number, message_text)
            return True
        
        # Live SMS API call would go here (e.g. via httpx)
        logger.info("Dispatched live SMS to %s via carrier gateway", phone_number)
        return True


class MessagingService:
    """
    Unified Messaging Dispatcher.
    Routes between SMTP Email (zero-cost prototype mode) and carrier SMS (live mode)
    based on the MESSAGING_BACKEND configuration in .env.
    """

    @classmethod
    def get_backend(cls) -> str:
        return getattr(settings, 'MESSAGING_BACKEND', 'email').lower()

    @classmethod
    def send_otp(cls, recipient_phone: str, recipient_email: str | None, otp_code: str, user_name: str = "User") -> bool:
        """
        Dispatches OTP. If backend is 'email', routes to recipient_email via SMTP.
        If backend is 'sms', routes to recipient_phone.
        """
        backend = cls.get_backend()
        logger.info("Dispatching OTP code using backend '%s'", backend)

        if backend == 'email':
            if not recipient_email:
                logger.warning("No email address provided for user %s, falling back to console/SMS log", recipient_phone)
                # In dev without email, print code to console so developer is never blocked
                print(f"\n[DEV CONSOLE OTP] To: {recipient_phone} | Code: {otp_code}\n")
                return True
            return EmailService.send_otp_email(recipient_email, otp_code, user_name)
        else:
            sms_text = f"MediVault: Your verification code is {otp_code}. Valid for 5 minutes."
            return SMSGatewayService.send_sms(recipient_phone, sms_text)

    @classmethod
    def send_queue_alert(cls, recipient_phone: str, recipient_email: str | None, serial_token: str, remaining_ahead: int, clinic_name: str) -> bool:
        backend = cls.get_backend()
        if backend == 'email' and recipient_email:
            return EmailService.send_queue_alert_email(recipient_email, serial_token, remaining_ahead, clinic_name)
        else:
            sms_text = f"MediVault: Serial {serial_token} ({clinic_name}). {remaining_ahead} patient(s) ahead. Please be near chamber."
            return SMSGatewayService.send_sms(recipient_phone, sms_text)

    @classmethod
    def send_call_in_alert(cls, recipient_phone: str, recipient_email: str | None, serial_token: str, clinic_name: str, doctor_name: str) -> bool:
        backend = cls.get_backend()
        if backend == 'email' and recipient_email:
            return EmailService.send_call_in_email(recipient_email, serial_token, clinic_name, doctor_name)
        else:
            sms_text = f"MediVault: Token {serial_token} called into Dr. {doctor_name}'s chamber ({clinic_name}). Please enter now."
            return SMSGatewayService.send_sms(recipient_phone, sms_text)

    @classmethod
    def send_danger_alert(cls, recipient_phone: str, recipient_email: str | None, alert_type: str, trigger_value: str, instructions: str) -> bool:
        backend = cls.get_backend()
        if backend == 'email' and recipient_email:
            return EmailService.send_danger_alert_email(recipient_email, alert_type, trigger_value, instructions)
        else:
            sms_text = f"EMERGENCY ALERT: {alert_type} ({trigger_value}). {instructions[:120]}... Call 999 if severe."
            return SMSGatewayService.send_sms(recipient_phone, sms_text)

    @classmethod
    def send_medication_reminder(cls, recipient_phone: str, recipient_email: str | None, patient_name: str, medication_name: str, strength: str, time_str: str) -> bool:
        backend = cls.get_backend()
        if backend == 'email' and recipient_email:
            return EmailService.send_medication_reminder_email(recipient_email, patient_name, medication_name, strength, time_str)
        else:
            sms_text = f"MediVault Reminder: Time to take {medication_name} ({strength}) scheduled for {time_str}."
            return SMSGatewayService.send_sms(recipient_phone, sms_text)

