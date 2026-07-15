from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import User


class StyledPasswordChangeForm(StyledFormMixin, PasswordChangeForm):
    pass


class EmailLoginForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(label=_("Email"))
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)


class TOTPForm(StyledFormMixin, forms.Form):
    code = forms.CharField(label=_("6-digit code"), max_length=6, min_length=6)


class RegisterForm(StyledFormMixin, UserCreationForm):
    class Meta:
        model = User
        fields = ["email", "full_name", "role", "department", "phone"]
        widgets = {
            "role": forms.Select(choices=[
                (r.value, r.label) for r in User.Role if r != User.Role.ADMIN
            ]),
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
