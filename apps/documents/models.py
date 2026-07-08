import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _


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
    file = models.FileField(upload_to="documents/%Y/%m/", blank=True, null=True)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} v{self.version}"


class DocumentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="versions")
    version_number = models.CharField(max_length=20)
    file = models.FileField(upload_to="documents/%Y/%m/")
    file_size = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    notes = models.CharField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.document.name} v{self.version_number}"


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
