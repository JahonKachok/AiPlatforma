from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Idempotently registers the hourly deadline check and the daily office-payment reminder (Zavxoz)."

    def handle(self, *args, **options):
        schedule, _created = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.HOURS)
        task, created = PeriodicTask.objects.update_or_create(
            name="check_deadlines",
            defaults={
                "interval": schedule,
                "task": "apps.notifications.tasks.check_deadlines",
                "enabled": True,
            },
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} periodic task '{task.name}' (hourly)."))

        daily, _created = CrontabSchedule.objects.get_or_create(
            minute="0", hour="9", day_of_week="*", day_of_month="*", month_of_year="*", timezone=settings.TIME_ZONE,
        )
        task, created = PeriodicTask.objects.update_or_create(
            name="zavxoz_office_payments",
            defaults={"crontab": daily, "interval": None, "enabled": True,
                      "task": "apps.ai_agents.tasks.remind_office_payments"},
        )
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} periodic task '{task.name}' (daily 09:00)."))
