import re
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.validators import MaxFileSizeValidator

_INVALID_PATH_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_path_segment(value):
    cleaned = _INVALID_PATH_CHARS.sub("", str(value)).strip(" .")
    return cleaned or "folder"


def task_upload_dir(task):
    """Проекты/<project>/Задачи/<sub_object>_<task>_<assignee>_<short id>/"""
    sub_object = task.section.sub_object if task.section_id else None
    subobject_part = sanitize_path_segment(sub_object.name) if sub_object else "Umumiy"
    title_part = sanitize_path_segment(task.title)
    assignee_part = sanitize_path_segment(task.assignee.full_name) if task.assignee_id else "Biriktirilmagan"
    short_id = str(task.id).split("-")[0]
    task_folder = f"{subobject_part}_{title_part}_{assignee_part}_{short_id}"
    project_part = sanitize_path_segment(task.project.name)
    return f"Проекты/{project_part}/Задачи/{task_folder}"


def task_attachment_upload_to(instance, filename):
    return f"{task_upload_dir(instance.task)}/{filename}"


class Task(models.Model):
    class Status(models.TextChoices):
        NEW = "new", _("New")
        IN_PROGRESS = "in_progress", _("In progress")
        REVIEW = "review", _("Review")
        REVISION = "revision", _("Needs revision")
        APPROVED = "approved", _("Approved")
        COMPLETED = "completed", _("Completed")

    class Priority(models.TextChoices):
        LOW = "low", _("Low")
        MEDIUM = "medium", _("Medium")
        HIGH = "high", _("High")
        CRITICAL = "critical", _("Critical")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="tasks")
    section = models.ForeignKey(
        "projects.Section", on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks"
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_tasks"
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_tasks"
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="review_tasks", verbose_name=_("Reviewer"),
        help_text=_("Who checks this task once it is sent for review."),
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.MEDIUM)
    deadline = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def is_overdue(self):
        from django.utils import timezone
        return bool(
            self.deadline
            and self.status not in (Task.Status.COMPLETED, Task.Status.APPROVED)
            and self.deadline < timezone.now().date()
        )


class TaskComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.user} on {self.task}"


class TaskAttachment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="attachments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file = models.FileField(upload_to=task_attachment_upload_to, validators=[MaxFileSizeValidator(25)])
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.filename
