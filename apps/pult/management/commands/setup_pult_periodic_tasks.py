from django_celery_beat.models import CrontabSchedule, PeriodicTask

from django.conf import settings
from django.core.management.base import BaseCommand

# Har kuni ishga tushadi; dam olish va bayram kunlarini vazifaning o'zi
# Pult kalendari bo'yicha o'tkazib yuboradi.
TASKS = [
    ("pult_daily_report_reminder", "apps.pult.tasks.remind_daily_reports", "30", "17", "har kuni 17:30"),
    ("pult_pending_decisions_digest", "apps.pult.tasks.digest_pending_decisions", "30", "8", "har kuni 08:30"),
]


class Command(BaseCommand):
    help = "Pult eslatmalarini (kunlik hisobot, qaror kutayotganlar) Celery Beat'da idempotent ro'yxatdan o'tkazadi."

    def handle(self, *args, **options):
        for name, task_path, minute, hour, label in TASKS:
            schedule, _created = CrontabSchedule.objects.get_or_create(
                minute=minute, hour=hour, day_of_week="*", day_of_month="*", month_of_year="*",
                timezone=settings.TIME_ZONE,
            )
            task, created = PeriodicTask.objects.update_or_create(
                name=name,
                defaults={"crontab": schedule, "interval": None, "task": task_path, "enabled": True},
            )
            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb} periodic task '{task.name}' ({label}, {settings.TIME_ZONE})."))
