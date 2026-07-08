import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Project(models.Model):
    class Stage(models.TextChoices):
        CONCEPT = "concept", _("Concept")
        PRELIMINARY = "preliminary", _("Preliminary design")
        WORKING_DOCS = "working_docs", _("Working documentation")
        EXPERTISE = "expertise", _("Expertise")
        CONSTRUCTION = "construction", _("Construction")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        ON_HOLD = "on_hold", _("On hold")
        COMPLETED = "completed", _("Completed")
        CANCELLED = "cancelled", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=2000, blank=True, null=True)
    client_name = models.CharField(max_length=255, blank=True, null=True)
    client_contact = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    stage = models.CharField(max_length=20, choices=Stage.choices, default=Stage.CONCEPT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    start_date = models.DateField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    budget = models.FloatField(default=0)
    paid_amount = models.FloatField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_projects"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    @property
    def paid_percentage(self):
        if not self.budget:
            return 0
        return min(100, round(self.paid_amount / self.budget * 100))


class SectionStatus(models.TextChoices):
    NOT_STARTED = "not_started", _("Not started")
    IN_PROGRESS = "in_progress", _("In progress")
    REVIEW = "review", _("Review")
    COMPLETED = "completed", _("Completed")


class SubObject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sub_objects")
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True, null=True)
    gip = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="gip_sub_objects",
    )
    status = models.CharField(max_length=20, choices=SectionStatus.choices, default=SectionStatus.NOT_STARTED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.project.name} / {self.name}"


class Section(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="sections")
    sub_object = models.ForeignKey(
        SubObject, on_delete=models.SET_NULL, null=True, blank=True, related_name="sections"
    )
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    gip = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="gip_sections",
    )
    status = models.CharField(max_length=20, choices=SectionStatus.choices, default=SectionStatus.NOT_STARTED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class ProjectMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="project_memberships"
    )
    role_in_project = models.CharField(max_length=100, blank=True, null=True)
    can_edit = models.BooleanField(default=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "user"], name="unique_project_member"),
        ]

    def __str__(self):
        return f"{self.user} @ {self.project}"

    def is_active(self):
        from django.utils import timezone
        return self.expires_at is None or self.expires_at > timezone.now()
