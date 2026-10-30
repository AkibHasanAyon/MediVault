from django.apps import AppConfig

class HealthLogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.health_logs'
    verbose_name = 'Daily Vitals & Danger Alerts'

    def ready(self):
        import apps.health_logs.signals  # noqa
