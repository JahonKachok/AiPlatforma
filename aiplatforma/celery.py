import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aiplatforma.settings.dev")

app = Celery("aiplatforma")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
