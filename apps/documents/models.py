import os
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.validators import AllowedExtensionsValidator, MaxFileSizeValidator


def _uploaded_name(field_file):
    """Yangi yuklangan (hali saqlanmagan) faylning foydalanuvchidagi asl nomi.
    Saqlashda Django nomni o'zgartirishi mumkin (probel → «_», takrorda
    «_AbC1234» qo'shimchasi) — yuklab olish/ZIP/Telegram'da asl nom kerak."""
    if field_file and not getattr(field_file, "_committed", True):
        return os.path.basename(field_file.name)[:255]
    return None


class DriveStatus(models.TextChoices):
    PENDING = "pending", _("Waiting for Drive")
    SYNCED = "synced", _("On Drive")
    ERROR = "error", _("Drive error")


class DocumentStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    REVIEW = "review", _("In review")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    ARCHIVED = "archived", _("Archived")


class ApprovalStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    REVISION = "revision", _("Needs revision")


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    doc_type = models.CharField(max_length=50, blank=True, null=True)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="documents")
    section = models.ForeignKey(
        "projects.Section", on_delete=models.SET_NULL, null=True, blank=True, related_name="documents"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="uploaded_documents"
    )
    version = models.CharField(max_length=20, default="1.0")
    status = models.CharField(max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.DRAFT)
    file = models.FileField(
        upload_to="documents/%Y/%m/", blank=True, null=True,
        validators=[MaxFileSizeValidator(50), AllowedExtensionsValidator()],
    )
    original_name = models.CharField(max_length=255, blank=True, default="", editable=False)
    # Joriy reviziyaning Google Drive'dagi fayli va papkasi (Arxivarius to'ldiradi).
    drive_file_id = models.CharField(max_length=128, blank=True, default="", editable=False)
    drive_folder_id = models.CharField(max_length=128, blank=True, default="", editable=False)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    source_task = models.OneToOneField(
        "tasks.Task", on_delete=models.SET_NULL, null=True, blank=True, related_name="approval_document",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} v{self.version}"

    def save(self, *args, **kwargs):
        self.original_name = _uploaded_name(self.file) or self.original_name
        super().save(*args, **kwargs)


class DocumentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_number = models.CharField(max_length=20)
    file = models.FileField(
        upload_to="documents/%Y/%m/",
        validators=[MaxFileSizeValidator(50), AllowedExtensionsValidator()],
    )
    original_name = models.CharField(max_length=255, blank=True, default="", editable=False)
    # Reviziyalar reyestri: hujjat ichidagi tartib raqami (1, 2, 3...).
    revision = models.PositiveIntegerField(default=0, editable=False)
    drive_status = models.CharField(max_length=10, choices=DriveStatus.choices, default=DriveStatus.PENDING, editable=False)
    drive_file_id = models.CharField(max_length=128, blank=True, default="", editable=False)
    drive_folder_id = models.CharField(max_length=128, blank=True, default="", editable=False)
    drive_error = models.CharField(max_length=500, blank=True, default="", editable=False)
    drive_synced_at = models.DateTimeField(null=True, blank=True, editable=False)
    in_old_folder = models.BooleanField(default=False, editable=False)
    file_size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    notes = models.CharField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.document.name} v{self.version_number}"

    def save(self, *args, **kwargs):
        name = _uploaded_name(self.file)
        if name:
            self.original_name = name
        elif not self.original_name and self.file and self.file.name == self.document.file.name:
            # Birinchi versiya hujjatning o'z faylini oladi (document_upload).
            self.original_name = self.document.original_name
        if self._state.adding and not self.revision:
            last = DocumentVersion.objects.filter(document_id=self.document_id).aggregate(m=models.Max("revision"))["m"]
            self.revision = (last or 0) + 1
        super().save(*args, **kwargs)


class DriveFolder(models.Model):
    """Drive papkalari keshi: «ildiz/Loyiha/Obyekt/Intizom» yo'li -> papka ID.
    Har yuklashda papkani Drive'dan qayta qidirmaslik uchun."""

    path = models.CharField(max_length=1000, unique=True)
    folder_id = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.path


class ApprovalStage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="approval_stages")
    stage_order = models.PositiveIntegerField()
    stage_name = models.CharField(max_length=100)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="approval_stages"
    )
    status = models.CharField(max_length=20, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING)
    comment = models.CharField(max_length=1000, blank=True, null=True)
    response_file = models.FileField(
        upload_to="approval_responses/%Y/%m/", blank=True, null=True,
        validators=[MaxFileSizeValidator(50), AllowedExtensionsValidator()],
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["stage_order"]

    def __str__(self):
        return f"{self.document.name} · stage {self.stage_order}: {self.stage_name}"


class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=64, null=True, blank=True)
    content_object = GenericForeignKey("content_type", "object_id")
    action = models.CharField(max_length=100)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="audit_logs"
    )
    details = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["content_type", "object_id"])]

    def __str__(self):
        return f"{self.action} on {self.content_type}#{self.object_id} @ {self.created_at:%Y-%m-%d %H:%M}"

    @classmethod
    def log(cls, *, obj, action, user=None, details=None, ip_address=None):
        return cls.objects.create(
            content_type=ContentType.objects.get_for_model(obj),
            object_id=str(obj.pk),
            action=action,
            user=user,
            details=details,
            ip_address=ip_address,
        )
