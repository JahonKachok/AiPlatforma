import base64
import io

import pyotp
import qrcode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views import View

from apps.core.permissions import role_required

from .forms import (
    EmailLoginForm,
    NotificationPreferenceForm,
    ProfileForm,
    RegisterForm,
    StyledPasswordChangeForm,
    TOTPForm,
    UserAdminEditForm,
    UserCreateForm,
)
from .models import LoginJournal, User

MANAGE_ROLES = (User.Role.ADMIN, User.Role.MANAGER)

SESSION_2FA_USER_ID = "2fa_pending_user_id"


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _log_login(request, user, status="success"):
    LoginJournal.objects.create(
        user=user,
        ip_address=_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
        status=status,
    )


class LoginView(View):
    template_name = "accounts/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return render(request, self.template_name, {"form": EmailLoginForm()})

    def post(self, request):
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"].lower()
            password = form.cleaned_data["password"]
            user = authenticate(request, username=email, password=password)
            if user is None:
                messages.error(request, _("Invalid email or password."))
                try:
                    bad_user = User.objects.get(email=email)
                    _log_login(request, bad_user, status="failed")
                except User.DoesNotExist:
                    pass
                return render(request, self.template_name, {"form": form})

            if user.two_factor_enabled:
                request.session[SESSION_2FA_USER_ID] = str(user.pk)
                return redirect("accounts:2fa_challenge")

            login(request, user)
            _log_login(request, user, status="success")
            return redirect(settings.LOGIN_REDIRECT_URL)
        return render(request, self.template_name, {"form": form})


class TwoFactorChallengeView(View):
    template_name = "accounts/2fa_challenge.html"

    def _pending_user(self, request):
        user_id = request.session.get(SESSION_2FA_USER_ID)
        if not user_id:
            return None
        return User.objects.filter(pk=user_id, two_factor_enabled=True).first()

    def get(self, request):
        if not self._pending_user(request):
            return redirect("accounts:login")
        return render(request, self.template_name, {"form": TOTPForm()})

    def post(self, request):
        user = self._pending_user(request)
        if not user:
            return redirect("accounts:login")
        form = TOTPForm(request.POST)
        if form.is_valid():
            totp = pyotp.TOTP(user.totp_secret)
            if totp.verify(form.cleaned_data["code"], valid_window=1):
                del request.session[SESSION_2FA_USER_ID]
                login(request, user)
                _log_login(request, user, status="success")
                return redirect(settings.LOGIN_REDIRECT_URL)
            messages.error(request, _("Invalid verification code."))
        return render(request, self.template_name, {"form": form})


def logout_view(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


class RegisterView(View):
    template_name = "accounts/register.html"

    def get(self, request):
        return render(request, self.template_name, {"form": RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Account created. You can now log in."))
            return redirect("accounts:login")
        return render(request, self.template_name, {"form": form})


@login_required
def profile_view(request):
    edit_mode = request.GET.get("edit") == "1"
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Profile updated."))
            return redirect("accounts:profile")
        edit_mode = True
    else:
        form = ProfileForm(instance=request.user)

    if request.method == "POST" and "prefs_submit" in request.POST:
        prefs_form = NotificationPreferenceForm(request.POST, instance=request.user.notification_preference)
        if prefs_form.is_valid():
            prefs_form.save()
            messages.success(request, _("Notification preferences saved."))
            return redirect("accounts:profile")
    else:
        prefs_form = NotificationPreferenceForm(instance=request.user.notification_preference)

    return render(request, "accounts/profile.html", {
        "form": form,
        "prefs_form": prefs_form,
        "edit_mode": edit_mode,
    })


class ChangePasswordView(PasswordChangeView):
    template_name = "accounts/change_password.html"
    form_class = StyledPasswordChangeForm
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _("Password changed."))
        return response


@login_required
def two_factor_setup(request):
    if request.user.two_factor_enabled:
        return redirect("accounts:profile")
    secret = request.session.get("pending_totp_secret")
    if not secret:
        secret = pyotp.random_base32()
        request.session["pending_totp_secret"] = secret

    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=request.user.email, issuer_name="AiPlatforma")
    qr_img = qrcode.make(uri)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode()

    if request.method == "POST":
        form = TOTPForm(request.POST)
        if form.is_valid():
            totp = pyotp.TOTP(secret)
            if totp.verify(form.cleaned_data["code"], valid_window=1):
                request.user.totp_secret = secret
                request.user.two_factor_enabled = True
                request.user.save(update_fields=["totp_secret", "two_factor_enabled"])
                del request.session["pending_totp_secret"]
                messages.success(request, _("Two-factor authentication enabled."))
                return redirect("accounts:profile")
            messages.error(request, _("Invalid verification code."))
    else:
        form = TOTPForm()

    return render(request, "accounts/2fa_setup.html", {
        "secret": secret,
        "qr_base64": qr_base64,
        "form": form,
    })


@login_required
def two_factor_disable(request):
    if request.method == "POST":
        form = TOTPForm(request.POST)
        if form.is_valid():
            totp = pyotp.TOTP(request.user.totp_secret)
            if totp.verify(form.cleaned_data["code"], valid_window=1):
                request.user.totp_secret = None
                request.user.two_factor_enabled = False
                request.user.save(update_fields=["totp_secret", "two_factor_enabled"])
                messages.success(request, _("Two-factor authentication disabled."))
                return redirect("accounts:profile")
            messages.error(request, _("Invalid verification code."))
    else:
        form = TOTPForm()
    return render(request, "accounts/2fa_disable.html", {"form": form})


@login_required
def login_journal(request):
    entries = request.user.login_journal.all()[:50]
    return render(request, "accounts/login_journal.html", {"entries": entries})


@login_required
def user_list(request):
    users = User.objects.all()
    role = request.GET.get("role")
    if role:
        users = users.filter(role=role)
    search = request.GET.get("search")
    if search:
        users = users.filter(full_name__icontains=search) | users.filter(email__icontains=search)

    return render(request, "accounts/user_list.html", {
        "users": users,
        "role": role or "",
        "search": search or "",
        "roles": User.Role.choices,
        "can_manage": request.user.is_superuser or request.user.role in MANAGE_ROLES,
        "stats": {
            "total": User.objects.count(),
            "active": User.objects.filter(is_active=True).count(),
            "gip": User.objects.filter(role=User.Role.GIP).count(),
            "designer": User.objects.filter(role=User.Role.DESIGNER).count(),
        },
    })


@role_required(*MANAGE_ROLES)
def user_create(request):
    temp_password = None
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            temp_password = user.temp_password
            messages.success(
                request,
                _("User created. Temporary password: %(password)s") % {"password": temp_password},
            )
            return redirect("accounts:user_list")
    else:
        form = UserCreateForm()
    return render(request, "accounts/user_form.html", {"form": form, "is_create": True})


@role_required(*MANAGE_ROLES)
def user_update(request, pk):
    user = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        form = UserAdminEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, _("User updated."))
            return redirect("accounts:user_list")
    else:
        form = UserAdminEditForm(instance=user)
    return render(request, "accounts/user_form.html", {"form": form, "user_obj": user, "is_create": False})
