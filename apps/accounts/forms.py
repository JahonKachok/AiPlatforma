from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import User


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
    class Meta:
        model = User
        fields = ["email", "full_name", "role", "department", "phone"]
        widgets = {
            "role": forms.Select(choices=[
                (r.value, r.label) for r in User.Role if r != User.Role.ADMIN
            ]),
        }
        help_texts = {
            "email": _("The email address used to sign in — this is used as your login."),
            "full_name": _("Your full name, shown to other employees under this name."),
            "role": _("Your role in the system — permissions and visible sections are set based on this."),
            "department": _("The name of the department you work in (free text)."),
            "phone": _("A contact phone number, e.g. +998901234567."),
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


class UserCreateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["email", "full_name", "role", "department", "phone"]
        help_texts = {
            "email": _("The new employee's email address, used as their login."),
            "full_name": _("The employee's full name."),
            "role": _("The employee's role in the system — permissions are set based on this."),
            "department": _("The name of the department the employee works in (free text)."),
            "phone": _("A contact phone number, e.g. +998901234567."),
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
            "full_name": _("The employee's full name."),
            "role": _("The employee's role in the system — permissions are set based on this."),
            "department": _("The name of the department the employee works in (free text)."),
            "phone": _("A contact phone number, e.g. +998901234567."),
            "is_active": _("If unchecked, the employee cannot sign in (the account is blocked, but its data is kept)."),
        }
