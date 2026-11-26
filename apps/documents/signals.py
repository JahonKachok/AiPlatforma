from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DocumentVersion


@receiver(post_save, sender=DocumentVersion)
def queue_drive_sync(sender, instance, created, **kwargs):
    """Har yangi reviziya (qaysi yo'l bilan yuklanmasin) Drive'ga navbatga qo'yiladi."""
    if created and instance.file:
        from .archivist import queue_sync

        queue_sync(instance)
