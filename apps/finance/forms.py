from django import forms

from apps.core.forms import StyledFormMixin

from .models import Contract, EmployeeContract, FinancialRecord


class FinancialRecordForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = FinancialRecord
        fields = ["type", "amount", "currency", "description", "category", "date", "status"]
        widgets = {"date": forms.DateInput(attrs={"type": "date"})}
        help_texts = {
            "type": "Yozuv turi — kirim (to'lov) yoki chiqim (xarajat).",
            "amount": "Summa miqdori.",
            "currency": "Summaning valyutasi.",
            "description": "Yozuv haqida qisqa izoh (ixtiyoriy).",
            "category": "Xarajat/kirim toifasi (ixtiyoriy).",
            "date": "Operatsiya sanasi.",
            "status": "Yozuvning holati (masalan: kutilmoqda, tasdiqlangan).",
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
            "client_name": "Shartnoma tuzilgan mijoz/tashkilot nomi.",
            "contract_number": "Shartnomaning raqami (noyob identifikator).",
            "amount": "Shartnoma summasi.",
            "signed_date": "Shartnoma imzolangan sana.",
            "deadline": "Shartnoma bo'yicha bajarish muddati.",
            "status": "Shartnomaning joriy holati.",
            "file": "Shartnoma faylini yuklash (ixtiyoriy).",
            "notes": "Qo'shimcha izohlar (ixtiyoriy).",
        }


class EmployeeContractForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = EmployeeContract
        fields = ["user", "project", "amount", "advance", "paid", "status", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}
        help_texts = {
            "user": "Shartnoma tuzilgan xodim.",
            "project": "Xodim ishlaydigan loyiha.",
            "amount": "Shartnoma bo'yicha umumiy summa.",
            "advance": "Xodimga berilgan avans summasi.",
            "paid": "Hozirgacha to'langan summa.",
            "status": "Shartnomaning joriy holati.",
            "notes": "Qo'shimcha izohlar (ixtiyoriy).",
        }
