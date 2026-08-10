import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

class RecordType(models.TextChoices):
    INCOME = "income", _("Income")
    EXPENSE = "expense", _("Expense")
    ADVANCE = "advance", _("Advance")
    PAYMENT = "payment", _("Salary")


class RecordStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    CONFIRMED = "confirmed", _("Confirmed")
    CANCELLED = "cancelled", _("Cancelled")


class ContractStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    ACTIVE = "active", _("Active")
    COMPLETED = "completed", _("Completed")
    TERMINATED = "terminated", _("Terminated")


class Currency(models.TextChoices):
    UZS = "UZS", _("So'm")
    USD = "USD", _("Dollar")


class Account(models.TextChoices):
    USD_BANK = "usd_bank", _("Dollar hisob")
    UZS_BANK = "uzs_bank", _("So'm hisob")
    USD_CASH = "usd_cash", _("Naqd pul (USD)")


ACCOUNT_CURRENCY = {
    Account.USD_BANK: Currency.USD,
    Account.UZS_BANK: Currency.UZS,
    Account.USD_CASH: Currency.USD,
}


class FinancialRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="financial_records")
    sub_object = models.ForeignKey(
        "projects.SubObject", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="financial_records", verbose_name=_("Object / pod-object"),
    )
    type = models.CharField(max_length=20, choices=RecordType.choices)
    account = models.CharField(
        max_length=20, choices=Account.choices, blank=True, null=True, verbose_name=_("Account"),
    )
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
        return -self.amount if self.type in (RecordType.EXPENSE, RecordType.ADVANCE, RecordType.PAYMENT) else self.amount


class EmployeeContract(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee_contracts"
    )
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="employee_contracts")
    sub_object = models.ForeignKey(
        "projects.SubObject", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employee_contracts", verbose_name=_("Object"),
    )
    pod_object = models.ForeignKey(
        "projects.SubObject", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employee_contracts_as_pod_object", verbose_name=_("Pod-object"),
    )
    amount = models.FloatField()
    currency = models.CharField(max_length=10, choices=Currency.choices, default=Currency.UZS)
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


class FinanceSettings(models.Model):
    """Singleton row (pk=1) holding company-wide finance settings, e.g. the
    manually-updated USD exchange rate used to combine multi-currency totals."""

    usd_rate = models.FloatField(default=12700)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    def __str__(self):
        return f"1 USD = {self.usd_rate} UZS"

    @classmethod
    def get_solo(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
