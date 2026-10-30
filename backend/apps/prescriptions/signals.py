import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.prescriptions.models import Prescription, PrescriptionMedication
from apps.medications.models import Medication
from apps.medications.services.schedule_builder import ScheduleBuilder
from apps.prescriptions.services.follow_up_service import FollowUpService
from apps.prescriptions.services.prescription_pdf import PrescriptionPDFBuilder

logger = logging.getLogger('medivault.prescriptions')

def sync_prescription_to_patient_roster(prescription: Prescription):
    """
    Closed-loop integration:
    Transforms clinician-authored prescription medications into active patient medications,
    creates customizable reminder slots, sets follow-up memory, and builds the PDF.
    """
    patient = prescription.patient

    # 1. Populate patient's active medication roster
    med_items = prescription.medications.all()
    created_meds = []
    for item in med_items:
        # Check if already synced
        active_med, created = Medication.objects.get_or_create(
            patient=patient,
            source_prescription=prescription,
            name=item.brand_name,
            defaults={
                "family_member": prescription.family_member,
                "generic_name": item.generic_name,
                "strength": item.strength,
                "dosage_pattern": item.frequency,
                "start_date": timezone.localdate(),
                "refill_remaining_doses": max(item.duration_days * 2, 30),
                "is_active": True,
                "provenance": Medication.Provenance.CLINICIAN_AUTHORED,
            }
        )
        if created:
            ScheduleBuilder.generate_reminders_for_medication(active_med)
            created_meds.append(active_med)

    # 2. Schedule follow-up memory milestones
    if prescription.follow_up_date:
        FollowUpService.schedule_follow_up_milestones(prescription)

    # 3. Generate PDF if not already present
    if not prescription.pdf_file:
        try:
            PrescriptionPDFBuilder.generate_pdf(prescription)
        except Exception as e:
            logger.error("Failed to generate PDF on prescription sync: %s", str(e))

    # 4. Broadcast real-time WebSocket alert to patient
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            group_name = f"user_{patient.user.id}_alerts"
            payload = {
                "type": "prescription.created",
                "data": {
                    "prescription_id": str(prescription.id),
                    "doctor_name": f"Dr. {prescription.doctor.user.full_name}",
                    "clinic_name": prescription.clinic.name if prescription.clinic else "Chamber Consultation",
                    "medications_count": len(med_items),
                    "created_at": prescription.created_at.isoformat(),
                }
            }
            async_to_sync(channel_layer.group_send)(group_name, payload)
    except Exception as ws_err:
        logger.warning("WebSocket alert skipped or channel layer offline: %s", str(ws_err))

    logger.info("Closed-loop prescription sync completed for prescription %s (%d medications synced)", prescription.id, len(created_meds))

