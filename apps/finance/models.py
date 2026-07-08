import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class RecordType(models.TextChoices):
    INCOME = "income", _("Income")
    EXPENSE = "expense", _("Expense")
    ADVANCE = "advance", _("Advance")
    PAYMENT = "payment", _("Payment")


class RecordStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    CONFIRMED = "confirmed", _("Confirmed")
    CANCELLED = "cancelled", _("Cancelled")


class ContractStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    COMPLETED = "completed", _("Completed")
    TERMINATED = "terminated", _("Terminated")


class FinancialRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="financial_records")
    type = models.CharField(max_length=20, choices=RecordType.choices)
    amount = models.FloatField()
    currency = models.CharField(max_length=10, default="UZS")
    description = models.CharField(max_length=500, blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=RecordStatus.choices, default=RecordStatus.PENDING)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.get_type_display()} {self.amount} ({self.project})"

    @property
    def signed_amount(self):
        return -self.amount if self.type == RecordType.EXPENSE else self.amount


class Contract(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="contracts")
    client_name = models.CharField(max_length=255)
    contract_number = models.CharField(max_length=100, blank=True, null=True)
    amount = models.FloatField()
    signed_date = models.DateField(blank=True, null=True)
    deadline = models.DateField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=ContractStatus.choices, default=ContractStatus.DRAFT)
    file = models.FileField(upload_to="contracts/%Y/%m/", blank=True, null=True)
    notes = models.CharField(max_length=1000, blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.client_name} — {self.contract_number or self.pk}"


class EmployeeContract(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee_contracts"
    )
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="employee_contracts")
    amount = models.FloatField()
    advance = models.FloatField(default=0)
    paid = models.FloatField(default=0)
    status = models.CharField(max_length=20, choices=ContractStatus.choices, default=ContractStatus.ACTIVE)
    notes = models.CharField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} @ {self.project}"

    @property
    def balance(self):
        return self.amount - self.paid
