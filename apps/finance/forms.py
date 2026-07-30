from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import Contract, Contractor, CostCode, EmployeeContract, FinancialRecord, PaymentRequest


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


class CostCodeForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = CostCode
        fields = ["code", "category", "budget"]
        help_texts = {
            "code": _("The CSI-style code, e.g. \"03-30-00\"."),
            "category": _("The category name, e.g. \"Concrete works\"."),
            "budget": _("The planned budget for this cost code."),
        }


class ContractorForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Contractor
        fields = ["name", "phone", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}
        help_texts = {
            "name": _("The contractor/organization's name."),
            "phone": _("A contact phone number (optional)."),
            "notes": _("Additional notes (optional)."),
        }


class PaymentRequestForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = PaymentRequest
        fields = ["sub_object", "cost_code", "contractor", "payment_type", "amount", "comment", "invoice_file"]
        widgets = {"comment": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "sub_object": _("The sub-object this payment relates to (optional)."),
            "cost_code": _("The budget line (cost code) this payment is charged against."),
            "contractor": _("The contractor/organization being paid."),
            "payment_type": _("The type of payment — subcontract, advance, or invoice."),
            "amount": _("The gross amount requested. A 5% retainage is withheld automatically."),
            "comment": _("A short note on what this payment is for (optional)."),
            "invoice_file": _("Attach the invoice/contract document (optional, max 25MB)."),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["sub_object"].queryset = project.sub_objects.all()
            self.fields["cost_code"].queryset = project.cost_codes.all()


class PaymentApprovalReviewForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(
        choices=[("approved", _("Approve")), ("rejected", _("Reject"))],
        widget=forms.RadioSelect,
        help_text=_("Your decision on this payment request."),
    )
    comment = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}),
        help_text=_("Write the reason for your decision or your comment (optional)."),
    )
