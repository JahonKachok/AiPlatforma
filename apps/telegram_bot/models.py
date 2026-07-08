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
