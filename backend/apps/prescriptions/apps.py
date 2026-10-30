from django.apps import AppConfig

class PrescriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.prescriptions'
    verbose_name = 'Digital Prescriptions & Interactions'

    def ready(self):
        import apps.prescriptions.signals  # noqa
