from django.conf import settings
from django.core.management.base import BaseCommand

from apps.documents import drive
from apps.documents.tasks import sync_pending_to_drive

TASK_NAME = "documents_drive_sync"


class Command(BaseCommand):
    help = ("Drive'ga tushmagan reviziyalarni yuklaydi. --schedule: buni har 30 daqiqada "
            "bajaradigan Celery Beat vazifasini idempotent ro'yxatdan o'tkazadi.")

    def add_arguments(self, parser):
        parser.add_argument("--schedule", action="store_true")
        parser.add_argument("--limit", type=int, default=200)

    def handle(self, *args, schedule=False, limit=200, **options):
        if schedule:
            from django_celery_beat.models import IntervalSchedule, PeriodicTask

            interval, _ = IntervalSchedule.objects.get_or_create(every=30, period=IntervalSchedule.MINUTES)
            PeriodicTask.objects.update_or_create(
                name=TASK_NAME,
                defaults={"interval": interval, "crontab": None, "enabled": True,
                          "task": "apps.documents.tasks.sync_pending_to_drive"},
            )
            self.stdout.write(self.style.SUCCESS(f"Periodic task '{TASK_NAME}' (every 30 min, {settings.TIME_ZONE})."))
            return
        if not drive.is_configured():
            self.stdout.write(self.style.WARNING("Google Drive is not configured (admin panel → Integrations)."))
            return
        self.stdout.write(self.style.SUCCESS(f"Uploaded: {sync_pending_to_drive(limit)}"))
