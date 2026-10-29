import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User
from apps.patients.models import PatientProfile
from apps.doctors.models import DoctorProfile

logger = logging.getLogger('medivault.accounts')

@receiver(post_save, sender=User)
def create_user_role_profile(sender, instance, created, **kwargs):
    """Automatically provision corresponding domain profile when a User is created."""
    if not created:
        return

    if instance.role == User.Role.PATIENT:
        PatientProfile.objects.get_or_create(user=instance)
        logger.info("Auto-created PatientProfile for user %s", instance.phone_number)

    elif instance.role == User.Role.DOCTOR:
        DoctorProfile.objects.get_or_create(
            user=instance,
            defaults={
                'bmdc_registration_number': f"TEMP-{str(instance.id)[:8].upper()}",
                'primary_specialty': 'General Practitioner',
                'degrees_qualifications': 'MBBS',
            }
        )
        logger.info("Auto-created pending DoctorProfile for user %s", instance.phone_number)

