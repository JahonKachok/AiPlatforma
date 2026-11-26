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


class AgentMemory(models.Model):
    """Foydalanuvchi tuzatishlari («eslab qol: matn ustma-ust tushmasin») —
    keyingi so'rovlarda shu agentning promptiga qisqa qoida bo'lib qo'shiladi.
    agent="*" — barcha agentlar uchun."""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, null=True, blank=True,
                             related_name="agent_memories")
    agent = models.CharField(max_length=32, default="*", db_index=True)
    text = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "AI xotira (tuzatish)"
        verbose_name_plural = "AI xotira (tuzatishlar)"

    def __str__(self):
        return f"{self.agent}: {self.text[:60]}"


class PendingAction(models.Model):
    """AI tushungan, lekin foydalanuvchi hali tasdiqlamagan amal (masalan, moliya
    yozuvi). Telegram tugmasi «ag:ok:<id>» bilan bajariladi."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="ai_pending_actions")
    kind = models.CharField(max_length=32)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    done_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} · {self.user_id}"


class OfficeEmployee(models.Model):
    key = models.SlugField(primary_key=True)
    name = models.CharField(max_length=60)
    role = models.CharField(max_length=80)
    description = models.CharField(max_length=240)


class OfficeLead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        CONTACTED = "contacted", "Bog‘lanildi"

    employee = models.ForeignKey(OfficeEmployee, on_delete=models.PROTECT)
    brief = models.TextField()
    price = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status, default=Status.NEW)
    created_at = models.DateTimeField(auto_now_add=True)


class OfficeTask(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        WORKING = "working", "Ishlayapti"
        READY = "ready", "Tayyor"
        ERROR = "error", "Xatolik"

    employee = models.ForeignKey(OfficeEmployee, on_delete=models.PROTECT)
    lead = models.ForeignKey(OfficeLead, on_delete=models.PROTECT, null=True, blank=True)
    brief = models.TextField()
    status = models.CharField(max_length=12, choices=Status, default=Status.NEW)
    run_token = models.UUIDField(null=True, editable=False)
    started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OfficeResult(models.Model):
    task = models.OneToOneField(OfficeTask, on_delete=models.CASCADE, related_name="result")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
