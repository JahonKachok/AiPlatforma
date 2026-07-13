from django_celery_beat.models import CrontabSchedule, PeriodicTask

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "AI muddat agentining kunlik (har kuni 08:00) Celery Beat vazifasini idempotent ro'yxatdan o'tkazadi."

    def handle(self, *args, **options):
        schedule, _created = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="8",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            timezone=settings.TIME_ZONE,
        )
        task, created = PeriodicTask.objects.update_or_create(
            name="ai_deadline_agent",
            defaults={
                "crontab": schedule,
                "interval": None,
                "task": "apps.ai_agents.tasks.run_deadline_agent",
                "enabled": True,
            },
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} periodic task '{task.name}' (har kuni 08:00, {settings.TIME_ZONE})."))
