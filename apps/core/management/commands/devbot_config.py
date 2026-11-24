"""Devbot sozlamalarini JSON ko'rinishida chiqaradi va heartbeat yozadi.

Faqat serverdagi devbot ishlatadi:
    docker exec aiplatforma_web python manage.py devbot_config --heartbeat '{"busy": false}'
"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.core import devbot


class Command(BaseCommand):
    help = "Devbot uchun sozlamalar (JSON) va holatni qayd qilish."

    def add_arguments(self, parser):
        parser.add_argument("--heartbeat", help="Devbot holati (JSON obyekt)")

    def handle(self, *args, **options):
        if options["heartbeat"]:
            try:
                data = json.loads(options["heartbeat"])
            except ValueError as exc:
                raise CommandError(f"--heartbeat JSON emas: {exc}")
            if not isinstance(data, dict):
                raise CommandError("--heartbeat JSON obyekt bo'lishi kerak")
            # Faqat kutilgan maydonlar — sahifada ko'rsatiladi.
            devbot.record_heartbeat({
                "busy": bool(data.get("busy")),
                "task": str(data.get("task") or "")[:200],
                "version": str(data.get("version") or "")[:40],
                "username": str(data.get("username") or "")[:64],
            })
        self.stdout.write(json.dumps(devbot.config()))
