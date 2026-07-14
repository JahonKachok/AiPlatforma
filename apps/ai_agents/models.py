"""AI-agent chaqiruvlari jurnali (AI Audit Logs).

Har bir AI so'rovi — provayderi, modeli, prompti, javobi va davomiyligi bilan —
shu yerga yoziladi. Log yozishdagi xato agent ishini to'xtatmasligi kerak
(services.ask_ai dagi try/except ga qarang).
"""
import uuid

from django.db import models


class AILog(models.Model):
    class Status(models.TextChoices):
        SUCCESS = "success", "Muvaffaqiyatli"
        EMPTY = "empty", "Bo'sh javob"
        ERROR = "error", "Xato"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.CharField(max_length=64, blank=True, db_index=True)
    provider = models.CharField(max_length=32, blank=True)
    model = models.CharField(max_length=64, blank=True)
    system = models.TextField(blank=True)
    prompt = models.TextField(blank=True)
    response = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    error = models.TextField(blank=True)
    duration_ms = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "AI log"
        verbose_name_plural = "AI loglar"

    def __str__(self):
        return f"{self.agent or 'ai'} · {self.provider} · {self.created_at:%Y-%m-%d %H:%M}"
