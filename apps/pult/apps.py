from django.apps import AppConfig


class PultConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pult'
    label = 'pult'
    verbose_name = "GASTEC Пульт"

    def ready(self):
        from . import signals  # noqa: F401
