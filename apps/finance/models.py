import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.core.validators import MaxFileSizeValidator


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
    file = models.FileField(
        upload_to="contracts/%Y/%m/", blank=True, null=True,
        validators=[MaxFileSizeValidator(25)],
    )
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


class CostCode(models.Model):
    """A CSI-style budget line (smeta) within a project — e.g. "03-30-00 —
    Beton ishlari" — used to track planned budget vs. actual spend."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="cost_codes")
    code = models.CharField(max_length=20)
    category = models.CharField(max_length=255)
    budget = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["project", "code"], name="unique_project_cost_code"),
        ]

    def __str__(self):
        return f"{self.code} — {self.category}"


class Contractor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50, blank=True, null=True)
    notes = models.CharField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PaymentType(models.TextChoices):
    SUBCONTRACT = "subcontract", _("Subcontract")
    ADVANCE = "advance", _("Advance")
    INVOICE = "invoice", _("Invoice")


class PaymentStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")


class PaymentApprovalStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    SKIPPED = "skipped", _("Skipped")


# Payment requests at or above this amount require the 3rd (Manager) approval stage.
MANAGER_APPROVAL_THRESHOLD = 10_000


class PaymentRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="payment_requests")
    sub_object = models.ForeignKey(
        "projects.SubObject", on_delete=models.SET_NULL, null=True, blank=True, related_name="payment_requests"
    )
    cost_code = models.ForeignKey(CostCode, on_delete=models.PROTECT, related_name="payment_requests")
    contractor = models.ForeignKey(Contractor, on_delete=models.PROTECT, related_name="payment_requests")
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.INVOICE)
    amount = models.FloatField()
    retainage_rate = models.FloatField(default=0.05)
    retainage_amount = models.FloatField(default=0)
    comment = models.CharField(max_length=1000, blank=True, null=True)
    invoice_file = models.FileField(
        upload_to="payment_requests/%Y/%m/", blank=True, null=True,
        validators=[MaxFileSizeValidator(25)],
    )
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payment_requests"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.contractor} — {self.amount} ({self.get_status_display()})"

    @property
    def net_amount(self):
        return self.amount - self.retainage_amount

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.retainage_amount = round(self.amount * self.retainage_rate, 2)
        super().save(*args, **kwargs)


class PaymentApprovalStage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_request = models.ForeignKey(PaymentRequest, on_delete=models.CASCADE, related_name="approval_stages")
    stage_order = models.PositiveIntegerField()
    stage_name = models.CharField(max_length=100)
    required_role = models.CharField(max_length=20, choices=User.Role.choices)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="payment_approval_stages",
    )
    status = models.CharField(
        max_length=20, choices=PaymentApprovalStatus.choices, default=PaymentApprovalStatus.PENDING
    )
    comment = models.CharField(max_length=1000, blank=True, null=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["stage_order"]

    def __str__(self):
        return f"{self.payment_request_id} · stage {self.stage_order}: {self.stage_name}"
