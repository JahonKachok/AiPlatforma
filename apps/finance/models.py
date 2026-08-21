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


class RecordCategory(models.TextChoices):
    RENT = "rent", _("Rent")
    TAX = "tax", _("Tax")
    UTILITIES = "utilities", _("Utilities")
    SUPPLIES = "supplies", _("Office supplies")
    MATERIALS = "materials", _("Materials")
    SALARY = "salary", _("Salary")
    OTHER = "other", _("Other")


class AdminExpensePeriod(models.TextChoices):
    MONTH = "month", _("Monthly")
    QUARTER = "quarter", _("Quarterly")
    YEAR = "year", _("Yearly")


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
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="financial_records",
        verbose_name=_("Project"),
    )
    sub_object = models.ForeignKey(
        "projects.SubObject", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="financial_records", verbose_name=_("Object / pod-object"),
    )
    type = models.CharField(max_length=20, choices=RecordType.choices, verbose_name=_("Type"))
    account = models.CharField(
        max_length=20, choices=Account.choices, blank=True, null=True, verbose_name=_("Account"),
    )
    amount = models.FloatField(verbose_name=_("Amount"))
    currency = models.CharField(max_length=10, default="UZS", verbose_name=_("Currency"))
    description = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("Description"))
    category = models.CharField(
        max_length=100, choices=RecordCategory.choices, blank=True, null=True, verbose_name=_("Category"),
    )
    date = models.DateField(verbose_name=_("Date"))
    status = models.CharField(
        max_length=20, choices=RecordStatus.choices, default=RecordStatus.PENDING, verbose_name=_("Status"),
    )
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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="employee_contracts",
        verbose_name=_("Employee"),
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="employee_contracts",
        verbose_name=_("Project"),
    )
    sub_object = models.ForeignKey(
        "projects.SubObject", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employee_contracts", verbose_name=_("Object"),
    )
    pod_object = models.ForeignKey(
        "projects.SubObject", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="employee_contracts_as_pod_object", verbose_name=_("Pod-object"),
    )
    amount = models.FloatField(verbose_name=_("Budget"))
    currency = models.CharField(
        max_length=10, choices=Currency.choices, default=Currency.UZS, verbose_name=_("Currency"),
    )
    advance = models.FloatField(default=0, verbose_name=_("Advance"))
    paid = models.FloatField(default=0, verbose_name=_("Paid"))
    status = models.CharField(
        max_length=20, choices=ContractStatus.choices, default=ContractStatus.ACTIVE, verbose_name=_("Status"),
    )
    notes = models.CharField(max_length=1000, blank=True, null=True, verbose_name=_("Notes"))
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


class AdminExpenseCategory(models.TextChoices):
    TAX = "tax", _("Tax")
    RENT = "rent", _("Rent")
    UTILITIES = "utilities", _("Utilities")
    SUPPLIES = "supplies", _("Office supplies")
    OTHER = "other", _("Other")


class FinanceCategory(models.Model):
    """Custom categories created dynamically by managers for project or admin finance tracking."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name=_("Category name"))
    type = models.CharField(
        max_length=20,
        choices=[("income", _("Income")), ("expense", _("Expense")), ("admin", _("Administrative"))],
        default="expense",
        verbose_name=_("Type"),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("Finance Category")
        verbose_name_plural = _("Finance Categories")

    def __str__(self):
        return self.name


class AdministrativeExpense(models.Model):
    """A recurring/fixed company-wide cost (tax, rent, utilities, office
    supplies) tracked separately from project cash flow, on a monthly,
    quarterly, or yearly basis."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=100, verbose_name=_("Category"))
    amount = models.FloatField(verbose_name=_("Amount"))
    currency = models.CharField(max_length=10, choices=Currency.choices, default=Currency.UZS, verbose_name=_("Currency"))
    period = models.CharField(max_length=10, choices=AdminExpensePeriod.choices, verbose_name=_("Period"))
    date = models.DateField(verbose_name=_("Date"))
    note = models.CharField(max_length=500, blank=True, null=True, verbose_name=_("Note"))
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.category} {self.amount} ({self.get_period_display()})"

