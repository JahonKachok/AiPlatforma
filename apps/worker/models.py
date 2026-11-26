"""Ishchi kompyuter (AutoCAD/Word/Excel o'rnatilgan, doim yoniq Windows PC)
uchun ish navbati. Kompyuter serverga o'zi ulanadi (worker/gaztek_worker.py):
ishni oladi, faylni yuklab oladi, bajaradi va natijani qaytaradi. Server
tashqaridan kompyuterga ulanmaydi — tarmoq sozlamasi shart emas."""
import uuid

from django.conf import settings
from django.db import models


class JobKind(models.TextChoices):
    GOST_FORMAT = "gost_format", "DWG · ГОСТ"
    DWG_PRINT = "dwg_print", "DWG → PDF + shtamp"
    DWG_TRANSLATE = "dwg_translate", "DWG tarjima"
    XLSX_TRANSLATE = "xlsx_translate", "Excel tarjima"
    DOCX_TO_PDF = "docx_to_pdf", "DOCX → PDF"
    NORM_CONTROL = "norm_control", "Normokontrol"


class JobStatus(models.TextChoices):
    QUEUED = "queued", "Navbatda"
    RUNNING = "running", "Bajarilmoqda"
    DONE = "done", "Tayyor"
    ERROR = "error", "Xato"


class WorkerJob(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    kind = models.CharField(max_length=20, choices=JobKind.choices)
    status = models.CharField(max_length=10, choices=JobStatus.choices, default=JobStatus.QUEUED, db_index=True)
    params = models.JSONField(default=dict, blank=True)
    document = models.ForeignKey("documents.Document", on_delete=models.CASCADE, related_name="worker_jobs")
    version = models.ForeignKey("documents.DocumentVersion", on_delete=models.CASCADE, related_name="+")
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name="+")
    # Natija kelgach bajariladigan qo'shimcha qadam (masalan, sekretar: direktorga imzoga yuborish).
    then = models.CharField(max_length=32, blank=True, default="")
    result = models.JSONField(default=dict, blank=True)
    result_document = models.ForeignKey("documents.Document", on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name="+")
    error = models.TextField(blank=True, default="")
    worker = models.CharField(max_length=64, blank=True, default="")
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Ishchi kompyuter ishi"
        verbose_name_plural = "Ishchi kompyuter ishlari"

    def __str__(self):
        return f"{self.get_kind_display()} · {self.document} · {self.status}"


class WorkerNode(models.Model):
    """Ulangan ishchi kompyuterlar (heartbeat): admin panelda «online» holati."""

    name = models.CharField(max_length=64, unique=True)
    last_seen = models.DateTimeField()
    kinds = models.JSONField(default=list, blank=True)
    version = models.CharField(max_length=32, blank=True, default="")

    def __str__(self):
        return self.name
