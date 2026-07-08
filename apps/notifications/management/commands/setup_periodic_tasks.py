from django_celery_beat.models import IntervalSchedule, PeriodicTask

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Idempotently registers the hourly deadline-check Celery Beat task."

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
