from django import forms
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import NotificationPreference, User


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


class NotificationPreferenceForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = NotificationPreference
        fields = [
            "notify_task", "notify_deadline", "notify_approval", "notify_comment",
            "notify_finance", "notify_document", "notify_system",
            "email_enabled", "telegram_enabled",
        ]


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
