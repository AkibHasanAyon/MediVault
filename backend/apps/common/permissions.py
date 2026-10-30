from rest_framework import permissions
from django.utils import timezone
from apps.sharing.models import ConsultationShare

class IsPatient(permissions.BasePermission):
    """Allows access strictly to authenticated patient accounts."""
    message = "Access restricted to registered patient accounts."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'PATIENT')


class IsDoctor(permissions.BasePermission):
    """Allows access strictly to verified doctor accounts."""
    message = "Access restricted to medical doctors."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'DOCTOR')


class IsClinicAssistant(permissions.BasePermission):
    """Allows access to clinic chamber assistants or staff."""
    message = "Access restricted to authorized clinic assistants."

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and (
                request.user.role in ['ASSISTANT', 'ADMIN'] or request.user.is_staff
            )
        )


class IsOwnerOrSharedDoctor(permissions.BasePermission):
    """
    Object-level permission allowing access to:
    1. The patient who owns the medical record.
    2. A doctor who has an active, non-expired ConsultationShare session for this patient.
    """
    message = "You do not have active clinical authorization to access this medical record."

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        # Identify target patient profile from object
        patient_profile = getattr(obj, 'patient', None)
        if not patient_profile and hasattr(obj, 'user'):
            patient_profile = getattr(obj.user, 'patient_profile', None)

        if not patient_profile:
            return False

        # 1. Patient self-access
        if request.user.role == 'PATIENT':
            return hasattr(request.user, 'patient_profile') and patient_profile == request.user.patient_profile

        # 2. Doctor access via active consultation handshake
        if request.user.role == 'DOCTOR':
            doctor_profile = getattr(request.user, 'doctor_profile', None)
            if not doctor_profile:
                return False

            has_active_share = ConsultationShare.objects.filter(
                patient=patient_profile,
                doctor=doctor_profile,
                is_active=True,
                expires_at__gt=timezone.now()
            ).exists()
            return has_active_share

        # 3. Superuser/Admin
        if request.user.is_staff or request.user.role == 'ADMIN':
            return True

        return False

