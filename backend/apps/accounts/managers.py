from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    """Custom user manager where phone_number is the unique identifier for auth."""

    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError(_('The Phone Number must be provided'))
        
        # Normalize email if provided
        if extra_fields.get('email'):
            extra_fields['email'] = self.normalize_email(extra_fields['email'])
        
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'ADMIN')
        extra_fields.setdefault('is_phone_verified', True)
        extra_fields.setdefault('is_email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(phone_number, password, **extra_fields)

