from django import forms
from django.db.models import F
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin
from apps.projects.models import SubObject

from .models import Account, AdministrativeExpense, EmployeeContract, FinancialRecord, RecordCategory, RecordType


class TransactionForm(StyledFormMixin, forms.ModelForm):
    pod_object = forms.ModelChoiceField(
        queryset=SubObject.objects.filter(parent__isnull=False).select_related("project", "parent"),
        required=False, label=_("Pod-object"),
        help_text=_("The specific pod-object this salary expense is allocated to (shown when category is Salary)."),
    )

    class Meta:
        model = FinancialRecord
        fields = ["project", "sub_object", "type", "account", "amount", "date", "category", "description"]
        widgets = {
            "type": forms.HiddenInput,
            "date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.TextInput(attrs={"inputmode": "decimal", "data-money-input": "true"}),
        }
        help_texts = {
            "project": _("The project this transaction belongs to."),
            "sub_object": _("The object/pod-object this transaction relates to (optional)."),
            "account": _("The account the money moves through — determines its currency."),
            "amount": _("The amount, in the account's currency."),
            "date": _("The date of the transaction."),
            "category": _("The expense/income category (optional)."),
            "description": _("A short description of the transaction (optional)."),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["type"].choices = [
            (RecordType.INCOME, RecordType.INCOME.label), (RecordType.EXPENSE, RecordType.EXPENSE.label),
        ]
        self.fields["account"].required = True
        self.fields["category"].required = False
        if user is not None:
            from apps.projects.permissions import visible_projects_for
            self.fields["project"].queryset = visible_projects_for(user)
        self.fields["sub_object"].queryset = SubObject.objects.select_related("project", "parent")

    def clean(self):
        cleaned = super().clean()
        project, sub_object = cleaned.get("project"), cleaned.get("sub_object")
        pod_object = cleaned.get("pod_object")
        if project and sub_object and sub_object.project_id != project.id:
            self.add_error("sub_object", _("This object does not belong to the selected project."))
        if pod_object and sub_object and pod_object.parent_id != sub_object.id:
            self.add_error("pod_object", _("This pod-object does not belong to the selected object."))
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        pod_object = self.cleaned_data.get("pod_object")
        if instance.category == RecordCategory.SALARY and pod_object:
            instance.sub_object = pod_object
        if commit:
            instance.save()
        return instance


class FinancialRecordForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FinancialRecord
        fields = ["type", "amount", "currency", "description", "category", "date", "status"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.TextInput(attrs={"inputmode": "decimal", "data-money-input": "true"}),
        }
        help_texts = {
            "type": _("The record type — income (payment) or expense."),
            "amount": _("The amount."),
            "currency": _("The amount's currency."),
            "description": _("A short description of the record (optional)."),
            "category": _("The expense/income category (optional)."),
            "date": _("The date of the transaction."),
            "status": _("The record's status (e.g. pending, confirmed)."),
        }


class EmployeeContractForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EmployeeContract
        fields = ["user", "project", "sub_object", "pod_object", "amount", "currency", "notes"]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 2}),
            "amount": forms.TextInput(attrs={"inputmode": "decimal", "data-money-input": "true"}),
        }
        help_texts = {
            "user": _("The employee the contract is with."),
            "project": _("The project the employee works on."),
            "sub_object": _("The object the employee is assigned to (optional)."),
            "pod_object": _("The pod-object the employee is assigned to (optional)."),
            "amount": _("The total amount under the contract."),
            "currency": _("The contract amount's currency."),
            "notes": _("Additional notes (optional)."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sub_object"].queryset = SubObject.objects.filter(parent__isnull=True)
        self.fields["pod_object"].queryset = SubObject.objects.filter(parent__isnull=False)


class AdministrativeExpenseForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = AdministrativeExpense
        fields = ["category", "amount", "currency", "period", "date", "note"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.TextInput(attrs={"inputmode": "decimal", "data-money-input": "true"}),
        }
        help_texts = {
            "category": _("The administrative expense category (tax, rent, utilities, etc.)."),
            "amount": _("The amount."),
            "currency": _("The amount's currency."),
            "period": _("Whether this expense recurs monthly, quarterly, or yearly."),
            "date": _("The date this expense is recorded for."),
            "note": _("Additional notes (optional)."),
        }


class EmployeeContractPayForm(StyledFormMixin, forms.Form):
    employee_contract = forms.ModelChoiceField(
        queryset=EmployeeContract.objects.none(),
        label=_("Employee contract"),
        help_text=_("The employee contract this payment is made against."),
    )
    amount = forms.FloatField(
        min_value=0.01, help_text=_("The amount being paid now."),
        widget=forms.TextInput(attrs={"inputmode": "decimal", "data-money-input": "true"}),
    )
    is_advance = forms.BooleanField(
        required=False, label=_("This is an advance"),
        help_text=_("Check if this payment is an advance rather than the final settlement."),
    )
    account = forms.ChoiceField(choices=Account.choices, help_text=_("The account the payment is made from."))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["employee_contract"].queryset = (
            EmployeeContract.objects.select_related("user", "project")
            .exclude(status__in=["completed", "terminated"])
            .filter(paid__lt=F("amount"))
        )
