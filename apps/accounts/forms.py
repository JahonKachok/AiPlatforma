from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import Discipline, User


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].help_text = _("Your current password used to sign in to your account.")
        self.fields["new_password1"].help_text = (
            _("The new password must be at least 8 characters long and cannot be entirely numeric.")
        )
        self.fields["new_password2"].help_text = _("Enter the new password again to avoid mistakes.")


class EmailLoginForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(
        label=_("Email"), help_text=_("The email address you registered with."),
    )
    password = forms.CharField(
        label=_("Password"), widget=forms.PasswordInput, help_text=_("The password set for your account."),
    )


class TOTPForm(StyledFormMixin, forms.Form):
    code = forms.CharField(
        label=_("6-digit code"), max_length=6, min_length=6,
        help_text=_("The 6-digit code shown in your authenticator app (Google Authenticator, etc.)."),
    )


class RegisterForm(StyledFormMixin, UserCreationForm):
    """Ochiq (autentifikatsiyasiz) ro'yxatdan o'tish formasi.

    ``role`` bu yerda ATAYLAB yo'q: rol — avtorizatsiya o'qi, shuning uchun uni
    faqat admin/menejer ``UserCreateForm``/``UserAdminEditForm`` orqali bera
    oladi. Aks holda har kim ``role=admin`` yuborib o'zini admin qilib
    ro'yxatdan o'tkazishi mumkin edi (widget'dagi choices faqat ko'rinishga
    ta'sir qiladi, validatsiya modeldagi to'liq choices bo'yicha ketadi).
    """

    class Meta:
        model = User
        fields = ["email", "full_name", "department", "phone"]
        help_texts = {
            "email": _("The email address used to sign in — this is used as your login."),
            "full_name": _("Your full name, shown to other employees under this name."),
            "department": _("The name of the department you work in (free text)."),
            "phone": _("A contact phone number, e.g. +998901234567."),
        }

    def clean_email(self):
        # Unique tekshiruvi ham normallashtirilgan qiymat ustida ketishi uchun
        # email'ni save() emas, clean bosqichida kichik harfga o'tkazamiz.
        return self.cleaned_data["email"].lower()

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.DESIGNER
        # Ochiq ro'yxatdan o'tgan hisob admin/menejer faollashtirmaguncha
        # kira olmaydi — aks holda internetdagi istalgan odam tizimga kirib,
        # xodimlar ro'yxati va boshqa ichki ma'lumotlarni ko'rardi.
        user.is_active = False
        if commit:
            user.save()
        return user


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "phone", "department", "avatar"]
        help_texts = {
            "full_name": _("Your full name, shown to other employees under this name."),
            "phone": _("A contact phone number, e.g. +998901234567."),
            "department": _("The name of the department you work in (free text)."),
            "avatar": _("Profile picture — a square image looks best."),
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


def is_admin(user):
    return user.is_superuser or user.role == User.Role.ADMIN


class AdminRoleLimitMixin:
    """Admin rolini faqat admin bera oladi. Busiz menejer o'zini yoki
    boshqasini admin qilib, faqat adminlarga ochiq amallarga (backup, butun
    baza nusxasi) kirish huquqini olardi."""

    def __init__(self, *args, requester=None, **kwargs):
        super().__init__(*args, **kwargs)
        if requester is not None and not is_admin(requester):
            self.fields["role"].choices = [
                choice for choice in self.fields["role"].choices if choice[0] != User.Role.ADMIN
            ]


class AdminPasswordMixin(forms.Form):
    """Admin xodimga parolni o'zi qo'yadi (yaratishda yoki tahrirlashda).

    Ikkala maydon ham ixtiyoriy: yaratishda bo'sh qolsa tasodifiy vaqtinchalik
    parol chiqariladi, tahrirlashda bo'sh qolsa parol o'zgarmaydi. Parol
    platformaning umumiy parol talablaridan (AUTH_PASSWORD_VALIDATORS) o'tadi."""

    password1 = forms.CharField(
        label=_("Password"), required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"), required=False, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=_("Enter the same password again to avoid mistakes."),
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        others = User.objects.filter(email__iexact=email)
        if self.instance.pk:
            others = others.exclude(pk=self.instance.pk)
        if others.exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return email

    def clean(self):
        cleaned = super().clean()
        p1, p2 = cleaned.get("password1") or "", cleaned.get("password2") or ""
        if p1 or p2:
            if p1 != p2:
                self.add_error("password2", _("The two passwords do not match."))
            else:
                user = self.instance
                for name in ("email", "full_name"):
                    if cleaned.get(name):
                        setattr(user, name, cleaned[name])
                try:
                    password_validation.validate_password(p1, user)
                except forms.ValidationError as error:
                    self.add_error("password1", error)
        return cleaned


class UserCreateForm(AdminRoleLimitMixin, AdminPasswordMixin, StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "full_name", "role", "department", "disciplines", "discipline_other", "phone"]
        widgets = {"disciplines": forms.CheckboxSelectMultiple}
        help_texts = {
            "email": _("The new employee's email address, used as their login."),
            "full_name": _("The employee's full name."),
            "role": _("The employee's role in the system — permissions are set based on this."),
            "department": _("The name of the department the employee works in (free text)."),
            "disciplines": _("The disciplines (specializations) the employee can work in — select all that apply."),
            "discipline_other": _("If the employee's discipline isn't listed above, specify it here (optional)."),
            "phone": _("A contact phone number, e.g. +998901234567."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].help_text = _(
            "The password the employee will sign in with. Leave blank to generate a random temporary password."
        )

    def save(self, commit=True):
        import secrets

        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        # Admin parolni o'zi kiritgan bo'lsa, uni yana ko'rsatish shart emas.
        temp_password = None if password else secrets.token_urlsafe(9)
        user.set_password(password or temp_password)
        if commit:
            user.save()
            self.save_m2m()
        user.temp_password = temp_password  # surfaced once to the creating admin, not persisted
        return user


class UserAdminEditForm(AdminRoleLimitMixin, AdminPasswordMixin, StyledFormMixin, forms.ModelForm):
    """Xodimni tahrirlash. Login (email) va parolni faqat admin o'zgartiradi:
    aks holda menejer boshqa xodimning (masalan, moliyachining) parolini
    almashtirib, uning nomidan tizimga kira olardi."""

    class Meta:
        model = User
        fields = ["email", "full_name", "role", "department", "disciplines", "discipline_other", "phone", "is_active"]
        widgets = {"disciplines": forms.CheckboxSelectMultiple}
        help_texts = {
            "email": _("The email address the employee signs in with (their login)."),
            "full_name": _("The employee's full name."),
            "role": _("The employee's role in the system — permissions are set based on this."),
            "department": _("The name of the department the employee works in (free text)."),
            "disciplines": _("The disciplines (specializations) the employee can work in — select all that apply."),
            "discipline_other": _("If the employee's discipline isn't listed above, specify it here (optional)."),
            "phone": _("A contact phone number, e.g. +998901234567."),
            "is_active": _("If unchecked, the employee cannot sign in (the account is blocked, but its data is kept)."),
        }

    def __init__(self, *args, requester=None, **kwargs):
        super().__init__(*args, requester=requester, **kwargs)
        if requester is not None and not is_admin(requester):
            for name in ("email", "password1", "password2"):
                del self.fields[name]
        else:
            self.fields["password1"].label = _("New password")
            self.fields["password1"].help_text = _(
                "Set a new password for the employee. Leave blank to keep the current password."
            )

    @property
    def password_changed(self):
        return bool(self.cleaned_data.get("password1"))

    def save(self, commit=True):
        user = super().save(commit=False)
        if self.cleaned_data.get("password1"):
            user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            self.save_m2m()
        return user


class DisciplineForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Discipline
        fields = ["code", "name"]
        help_texts = {
            "code": _("A short unique code, e.g. AR, KR."),
            "name": _("The discipline's full name."),
        }
