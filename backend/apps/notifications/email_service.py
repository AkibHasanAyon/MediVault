import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger('medivault.notifications')

class EmailService:
    """
    SMTP Email Service for MediVault.
    Handles transactional health emails during development & production.
    """

    @staticmethod
    def send_otp_email(to_email: str, otp_code: str, user_name: str = "User") -> bool:
        subject = f"[MediVault] Your Verification Code: {otp_code}"
        message = (
            f"Dear {user_name},\n\n"
            f"Your MediVault 6-digit verification code is: {otp_code}\n\n"
            f"This code will expire in 5 minutes. Do not share this code with anyone.\n\n"
            f"If you did not request this code, please ignore this email.\n\n"
            f"— MediVault Health Care Team (Bangladesh)"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            logger.info("Successfully dispatched OTP email to %s", to_email)
            return True
        except Exception as e:
            logger.error("Failed to dispatch OTP email to %s: %s", to_email, str(e))
            return False

    @staticmethod
    def send_queue_alert_email(to_email: str, serial_token: str, remaining_ahead: int, clinic_name: str) -> bool:
        subject = f"[MediVault Queue Alert] Your Turn is Coming Up — Token {serial_token}"
        message = (
            f"Dear Patient,\n\n"
            f"আপনার সিরিয়াল নং {serial_token} ({clinic_name})।\n"
            f"আপনার পূর্বে আর {remaining_ahead} জন রোগী আছেন। অনুগ্রহ করে ডাক্তারের চেম্বারের সামনে প্রস্তুত থাকুন।\n\n"
            f"Token: {serial_token}\n"
            f"Clinic: {clinic_name}\n\n"
            f"— MediVault Chamber Desk"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error("Failed to send queue alert email to %s: %s", to_email, str(e))
            return False

    @staticmethod
    def send_danger_alert_email(to_email: str, alert_type: str, trigger_value: str, instruction_text: str) -> bool:
        subject = f"🚨 URGENT HEALTH ALERT: {alert_type} Detected ({trigger_value})"
        message = (
            f"EMERGENCY HEALTH WARNING:\n\n"
            f"A critical health reading was logged: {alert_type} ({trigger_value}).\n\n"
            f"IMMEDIATE ACTION REQUIRED:\n"
            f"{instruction_text}\n\n"
            f"If symptoms persist or worsen, please call national emergency services (999) or visit the nearest hospital emergency room immediately.\n\n"
            f"— MediVault Clinical Safety Monitor"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error("Failed to dispatch danger alert email to %s: %s", to_email, str(e))
            return False

    @staticmethod
    def send_medication_reminder_email(to_email: str, patient_name: str, medication_name: str, strength: str, time_str: str) -> bool:
        subject = f"⏰ Medication Reminder: {medication_name} ({strength})"
        message = (
            f"Dear {patient_name},\n\n"
            f"It is time to take your scheduled medication:\n\n"
            f"• Medication: {medication_name} ({strength})\n"
            f"• Scheduled Time: {time_str}\n\n"
            f"Please mark this dose as taken in your MediVault app.\n"
            f"Note: Never take a double dose if you previously missed one.\n\n"
            f"— MediVault Daily Health Desk"
        )
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            logger.error("Failed to dispatch medication reminder email to %s: %s", to_email, str(e))
            return False

