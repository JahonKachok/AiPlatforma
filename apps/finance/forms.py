from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import Contract, EmployeeContract, FinancialRecord


class FinancialRecordForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FinancialRecord
        fields = ["type", "amount", "currency", "description", "category", "date", "status"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
        help_texts = {
            "type": _("The record type — income (payment) or expense."),
            "amount": _("The amount."),
            "currency": _("The amount's currency."),
            "description": _("A short description of the record (optional)."),
            "category": _("The expense/income category (optional)."),
            "date": _("The date of the transaction."),
            "status": _("The record's status (e.g. pending, confirmed)."),
        }


class ContractForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Contract
        fields = ["client_name", "contract_number", "amount", "signed_date", "deadline", "status", "file", "notes"]
        widgets = {
            "signed_date": forms.DateInput(attrs={"type": "date"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }
        help_texts = {
            "client_name": _("The name of the client/organization the contract is with."),
            "contract_number": _("The contract number (a unique identifier)."),
            "amount": _("The contract amount."),
            "signed_date": _("The date the contract was signed."),
            "deadline": _("The contract's deadline."),
            "status": _("The contract's current status."),
            "file": _("Upload the contract file (optional)."),
            "notes": _("Additional notes (optional)."),
        }


class EmployeeContractForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EmployeeContract
        fields = ["user", "project", "amount", "advance", "paid", "status", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}
        help_texts = {
            "user": _("The employee the contract is with."),
            "project": _("The project the employee works on."),
            "amount": _("The total amount under the contract."),
            "advance": _("The advance amount given to the employee."),
            "paid": _("The amount paid so far."),
            "status": _("The contract's current status."),
            "notes": _("Additional notes (optional)."),
        }
