import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class TelegramLinkToken(models.Model):
    """Persisted replacement for the previous app's in-memory linking-token
    dict, which lost all pending links on every process restart."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="telegram_link_tokens"
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} · {self.token}"

    @classmethod
    def issue(cls, user, ttl_minutes=30):
        cls.objects.filter(user=user, used_at__isnull=True).delete()
        return cls.objects.create(
            user=user,
            token=uuid.uuid4().hex,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
        )

    def is_valid(self):
        return self.used_at is None and self.expires_at > timezone.now()


class TelegramChat(models.Model):
    """Chat darajasidagi bot sozlamalari (hozircha faqat til).

    User modeliga bog'lanmagan, chunki til hisob ulanmasdan oldin ham
    tanlanishi mumkin."""

    class Language(models.TextChoices):
        UZBEK = "uz", "Oʻzbekcha"
        RUSSIAN = "ru", "Русский"
        ENGLISH = "en", "English"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat_id = models.CharField(max_length=64, unique=True, db_index=True)
    language = models.CharField(max_length=8, choices=Language.choices, default=Language.UZBEK)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.chat_id} · {self.language}"


class TelegramEvent(models.Model):
    """Botga kelgan xabar va buyruqlar jurnali.

    Keyinchalik Telegram AI tahlili (topshiriqlarni ajratib olish, muhokama
    tahlili) uchun xomashyo bo'lib xizmat qiladi."""

    class Kind(models.TextChoices):
        COMMAND = "command", "Buyruq"
        MESSAGE = "message", "Xabar"
        OTHER = "other", "Boshqa"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="telegram_events",
    )
    chat_id = models.CharField(max_length=64, db_index=True)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.MESSAGE)
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Telegram hodisa"
        verbose_name_plural = "Telegram hodisalar"

    def __str__(self):
        return f"{self.chat_id} · {self.kind} · {self.created_at:%Y-%m-%d %H:%M}"
