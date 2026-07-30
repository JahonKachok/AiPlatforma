from pathlib import Path

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Task, task_upload_dir


@receiver(post_save, sender=Task)
def create_task_folder(sender, instance, created, **kwargs):
    if not created:
        return
    folder = Path(settings.MEDIA_ROOT) / task_upload_dir(instance)
    folder.mkdir(parents=True, exist_ok=True)
