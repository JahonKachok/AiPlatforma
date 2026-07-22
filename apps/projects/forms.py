from django import forms

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin

from .models import Project, ProjectMember, Section, SubObject


class ProjectForm(StyledFormMixin, forms.ModelForm):
    gip = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=[User.Role.GIP, User.Role.MANAGER, User.Role.ADMIN]),
        required=False, label="GIP",
        help_text="Loyihaning bosh inshoot arxitektori (GIP) — loyihaga mas'ul xodim (ixtiyoriy).",
    )

    class Meta:
        model = Project
        fields = [
            "name", "description", "client_name", "client_contact", "address",
            "stage", "status", "start_date", "deadline", "budget", "paid_amount",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "name": "Loyihaning nomi — ro'yxatda va hisobotlarda shu nom bilan ko'rinadi.",
            "description": "Loyiha haqida qisqa tavsif (ixtiyoriy).",
            "client_name": "Buyurtmachi (mijoz) tashkilot yoki shaxsning nomi.",
            "client_contact": "Buyurtmachining aloqa ma'lumoti — telefon yoki email.",
            "address": "Loyiha (qurilish) manzili.",
            "stage": "Loyihaning joriy bosqichi (masalan: loyihalash, qurilish).",
            "status": "Loyihaning holati (faol, to'xtatilgan, yakunlangan va h.k.).",
            "start_date": "Loyiha boshlangan sana.",
            "deadline": "Loyihani yakunlash uchun belgilangan muddat.",
            "budget": "Loyihaning umumiy byudjeti (summa).",
            "paid_amount": "Hozirgacha to'langan summa — byudjetdan qancha qismi to'langanini ko'rsatadi.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        gip_field = self.fields.pop("gip")
        self.fields["gip"] = gip_field

    def save(self, commit=True):
        project = super().save(commit=commit)
        gip = self.cleaned_data.get("gip")
        if commit and gip:
            ProjectMember.objects.update_or_create(
                project=project, user=gip, defaults={"role_in_project": "gip"}
            )
        return project


class ProjectMemberForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectMember
        fields = ["user", "role_in_project", "can_edit", "expires_at"]
        widgets = {"expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}
        help_texts = {
            "user": "Loyihaga qo'shilayotgan xodim.",
            "role_in_project": "Xodimning loyihadagi roli (masalan: GIP, muhandis).",
            "can_edit": "Belgilansa, xodim loyiha ma'lumotlarini tahrirlashi mumkin.",
            "expires_at": "Xodimning loyihaga kirish huquqi tugaydigan sana (ixtiyoriy).",
        }


class SubObjectForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SubObject
        fields = ["name", "address", "gip", "status"]
        help_texts = {
            "name": "Sub-obyekt nomi.",
            "address": "Sub-obyektning manzili (ixtiyoriy).",
            "gip": "Sub-obyektga mas'ul bosh inshoot arxitektori (GIP) (ixtiyoriy).",
            "status": "Sub-obyektning joriy holati.",
        }


class SectionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Section
        fields = ["sub_object", "code", "name", "gip", "status"]
        help_texts = {
            "sub_object": "Bo'lim qaysi sub-obyektga tegishli ekanligi.",
            "code": "Bo'lim uchun qisqa kod.",
            "name": "Bo'limning nomi.",
            "gip": "Bo'limga mas'ul bosh inshoot arxitektori (GIP) (ixtiyoriy).",
            "status": "Bo'limning joriy holati.",
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["sub_object"].queryset = project.sub_objects.all()
