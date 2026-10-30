import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import BloodGlucoseLog, BloodPressureLog
from .alert_engine import DangerAlertEngine
from .tasks import dispatch_danger_alert_task

logger = logging.getLogger('medivault.alerts')

@receiver(post_save, sender=BloodGlucoseLog)
def on_glucose_logged(sender, instance, created, **kwargs):
    """
    Evaluates newly logged glucose against clinical danger thresholds.
    Triggers alert creation and emergency dispatch if outside safe limits.
    """
    if not created:
        return

    alert = DangerAlertEngine.evaluate_glucose(instance)
    if alert:
        instance.is_danger = True
        instance.save(update_fields=['is_danger'])
        dispatch_danger_alert_task.delay(str(alert.id))


@receiver(post_save, sender=BloodPressureLog)
def on_blood_pressure_logged(sender, instance, created, **kwargs):
    """
    Evaluates newly logged BP against Hypertensive Crisis thresholds.
    Triggers alert creation and emergency dispatch if Systolic > 180 OR Diastolic > 120.
    """
    if not created:
        return

    alert = DangerAlertEngine.evaluate_blood_pressure(instance)
    if alert:
        instance.is_crisis = True
        instance.save(update_fields=['is_crisis'])
        dispatch_danger_alert_task.delay(str(alert.id))

