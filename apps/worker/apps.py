from django.apps import AppConfig


class WorkerConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.worker"
    label = "worker"
    verbose_name = "Ishchi kompyuter"
