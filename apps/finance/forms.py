from django import forms

from apps.core.forms import StyledFormMixin

from .models import Contract, EmployeeContract, FinancialRecord


class FinancialRecordForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FinancialRecord
        fields = ["type", "amount", "currency", "description", "category", "date", "status"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}


class ContractForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Contract
        fields = ["client_name", "contract_number", "amount", "signed_date", "deadline", "status", "file", "notes"]
        widgets = {
            "signed_date": forms.DateInput(attrs={"type": "date"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class EmployeeContractForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EmployeeContract
        fields = ["user", "project", "amount", "advance", "paid", "status", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}
