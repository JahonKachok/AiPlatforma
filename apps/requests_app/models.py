import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class RequestType(models.TextChoices):
    CHANGE = "change", _("Change")
    CLARIFICATION = "clarification", _("Clarification")
    IMPROVEMENT = "improvement", _("Improvement")
    ISSUE = "issue", _("Issue")


class RequestStatus(models.TextChoices):
    OPEN = "open", _("Open")
    IN_PROGRESS = "in_progress", _("In progress")
    RESOLVED = "resolved", _("Resolved")
    CLOSED = "closed", _("Closed")


class RequestPriority(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")


class Request(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=20, choices=RequestType.choices, default=RequestType.CLARIFICATION)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, null=True, blank=True, related_name="requests"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_requests"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_requests"
    )
    status = models.CharField(max_length=20, choices=RequestStatus.choices, default=RequestStatus.OPEN)
    priority = models.CharField(max_length=20, choices=RequestPriority.choices, default=RequestPriority.MEDIUM)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class RequestComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user} on {self.request}"
