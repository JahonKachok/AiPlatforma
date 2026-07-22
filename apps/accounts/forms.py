from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import User


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].help_text = "Hisobingizga kirish uchun ishlatadigan joriy parolingiz."
        self.fields["new_password1"].help_text = (
            "Yangi parol kamida 8 belgidan iborat bo'lishi va faqat raqamlardan tashkil topmasligi kerak."
        )
        self.fields["new_password2"].help_text = "Xatolikka yo'l qo'ymaslik uchun yangi parolni qayta kiriting."


class EmailLoginForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(
        label=_("Email"), help_text="Ro'yxatdan o'tishda ko'rsatgan email manzilingiz.",
    )
    password = forms.CharField(
        label=_("Password"), widget=forms.PasswordInput, help_text="Hisobingiz uchun belgilangan parol.",
    )


class TOTPForm(StyledFormMixin, forms.Form):
    code = forms.CharField(
        label=_("6-digit code"), max_length=6, min_length=6,
        help_text="Autentifikator ilovangizda (Google Authenticator va h.k.) ko'rsatilayotgan 6 xonali kod.",
    )


class RegisterForm(StyledFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ["email", "full_name", "role", "department", "phone"]
        widgets = {
            "role": forms.Select(choices=[
                (r.value, r.label) for r in User.Role if r != User.Role.ADMIN
            ]),
        }
        help_texts = {
            "email": "Tizimga kirish uchun ishlatiladigan email manzil — login sifatida shu ishlatiladi.",
            "full_name": "Ism va familiyangiz to'liq holda, boshqa xodimlarga shu nom bilan ko'rinadi.",
            "role": "Tizimdagi rolingiz — huquqlar va ko'rinadigan bo'limlar shu bo'yicha belgilanadi.",
            "department": "Ishlaydigan bo'limingiz nomi (erkin matn).",
            "phone": "Aloqa uchun telefon raqam, masalan: +998901234567.",
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        if commit:
            user.save()
        return user


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "phone", "department", "avatar"]
        help_texts = {
            "full_name": "Ism va familiyangiz, boshqa xodimlarga shu nom bilan ko'rinadi.",
            "phone": "Aloqa uchun telefon raqam, masalan: +998901234567.",
            "department": "Ishlaydigan bo'limingiz nomi (erkin matn).",
            "avatar": "Profil rasmi — kvadrat shakldagi rasm eng yaxshi ko'rinadi.",
        }


NOTIFICATION_TYPE_LABELS = {
    "task": _("Task assigned"),
    "deadline": _("Deadline approaching"),
    "approval": _("Approval required"),
    "comment": _("New comment"),
    "finance": _("Finance update"),
    "document": _("Document uploaded"),
    "system": _("System notices"),
}


class NotificationPreferenceForm(forms.Form):
    """Hodisa turi × kanal (sayt/email/telegram) switch matritsasi.

    Maydon nomlari: <type>_<channel> (masalan, task_email)."""

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        from .models import NOTIFICATION_CHANNELS, NOTIFICATION_TYPES

        for ntype in NOTIFICATION_TYPES:
            for channel in NOTIFICATION_CHANNELS:
                initial = instance.allows_channel(ntype, channel) if instance else True
                self.fields[f"{ntype}_{channel}"] = forms.BooleanField(
                    required=False, initial=initial
                )

    def save(self):
        from .models import NOTIFICATION_CHANNELS, NOTIFICATION_TYPES

        self.instance.channels = {
            ntype: {
                channel: self.cleaned_data.get(f"{ntype}_{channel}", False)
                for channel in NOTIFICATION_CHANNELS
            }
            for ntype in NOTIFICATION_TYPES
        }
        self.instance.save(update_fields=["channels"])
        return self.instance

    def rows(self):
        """Shablon uchun: (yorliq, [sayt, email, telegram maydonlari]) qatorlari."""
        from .models import NOTIFICATION_CHANNELS, NOTIFICATION_TYPES

        for ntype in NOTIFICATION_TYPES:
            yield (
                NOTIFICATION_TYPE_LABELS.get(ntype, ntype),
                [self[f"{ntype}_{channel}"] for channel in NOTIFICATION_CHANNELS],
            )


class UserCreateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "full_name", "role", "department", "phone"]
        help_texts = {
            "email": "Yangi xodimning login sifatida ishlatiladigan email manzili.",
            "full_name": "Xodimning to'liq ismi.",
            "role": "Xodimning tizimdagi roli — huquqlar shu bo'yicha belgilanadi.",
            "department": "Xodim ishlaydigan bo'lim nomi (erkin matn).",
            "phone": "Aloqa uchun telefon raqam, masalan: +998901234567.",
        }

    def save(self, commit=True):
        import secrets

        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        temp_password = secrets.token_urlsafe(9)
        user.set_password(temp_password)
        if commit:
            user.save()
        user.temp_password = temp_password  # surfaced once to the creating admin, not persisted
        return user


class UserAdminEditForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "role", "department", "phone", "is_active"]
        help_texts = {
            "full_name": "Xodimning to'liq ismi.",
            "role": "Xodimning tizimdagi roli — huquqlar shu bo'yicha belgilanadi.",
            "department": "Xodim ishlaydigan bo'lim nomi (erkin matn).",
            "phone": "Aloqa uchun telefon raqam, masalan: +998901234567.",
            "is_active": "O'chirilsa, xodim tizimga kira olmaydi (hisob bloklanadi, lekin ma'lumotlari saqlanib qoladi).",
        }
