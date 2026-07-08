import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DepartmentStatus(models.TextChoices):
    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")
    ARCHIVED = "archived", _("Archived")


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    description = models.CharField(max_length=1000, blank=True, null=True)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="headed_departments"
    )
    status = models.CharField(max_length=20, choices=DepartmentStatus.choices, default=DepartmentStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class OrganizationalUnit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="units")
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, null=True)
    description = models.CharField(max_length=1000, blank=True, null=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_units"
    )
    level = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=DepartmentStatus.choices, default=DepartmentStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.department.name} / {self.name}"


class DepartmentMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    unit = models.ForeignKey(OrganizationalUnit, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="department_memberships"
    )
    role_in_unit = models.CharField(max_length=100, blank=True, null=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="direct_reports_in_units",
    )
    is_primary = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-is_primary", "joined_at"]

    def __str__(self):
        return f"{self.user} @ {self.unit}"


class ReportingRelationship(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subordinate_relationships"
    )
    subordinate = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="manager_relationships"
    )
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True, related_name="reporting_relationships"
    )
    is_direct = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.subordinate} reports to {self.manager}"
