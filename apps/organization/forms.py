from django import forms

from apps.core.forms import StyledFormMixin

from .models import Department, DepartmentMember, OrganizationalUnit


class DepartmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name", "code", "description", "head", "status"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Bo'lim nomi (masalan: Qurilish bo'limi)"}),
            "code": forms.TextInput(attrs={"placeholder": "Kodi (masalan: QUR-01)"}),
            "description": forms.Textarea(attrs={"rows": 2, "placeholder": "Tavsif (ixtiyoriy)"}),
        }
        help_texts = {
            "name": "Bo'limning nomi — ro'yxatda shu nom bilan ko'rinadi.",
            "code": "Bo'lim uchun noyob qisqa kod, boshqa bo'limlarda takrorlanmasligi kerak.",
            "description": "Bo'lim haqida qisqa izoh (ixtiyoriy).",
            "head": "Shu bo'limga mas'ul rahbar xodim (ixtiyoriy).",
            "status": "Bo'limning joriy holati: Faol, Nofaol yoki Arxivlangan.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["head"].empty_label = "Rahbar (ixtiyoriy)"


class OrganizationalUnitForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = OrganizationalUnit
        fields = ["name", "code", "description", "manager", "level", "status"]
        widgets = {"description": forms.Textarea(attrs={"rows": 2})}
        help_texts = {
            "name": "Bo'linmaning nomi.",
            "code": "Bo'linma uchun qisqa kod (ixtiyoriy).",
            "description": "Bo'linma haqida qisqa izoh (ixtiyoriy).",
            "manager": "Shu bo'linmaga mas'ul menejer (ixtiyoriy).",
            "level": "Bo'linmaning ierarxik darajasi (raqam).",
            "status": "Bo'linmaning joriy holati.",
        }


class DepartmentMemberForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = DepartmentMember
        fields = ["user", "role_in_unit", "manager", "is_primary"]
        help_texts = {
            "user": "Bo'linmaga qo'shilayotgan xodim.",
            "role_in_unit": "Xodimning shu bo'linmadagi lavozimi/roli (erkin matn).",
            "manager": "Xodimning bevosita rahbari (ixtiyoriy).",
            "is_primary": "Belgilansa, bu xodimning asosiy (birlamchi) bo'linmasi hisoblanadi.",
        }
