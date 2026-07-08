import pyotp
from django.test import TestCase
from django.urls import reverse

from .models import User


class AuthFlowTests(TestCase):
    def setUp(self):
        self.password = "s3curePass!23"
        self.user = User.objects.create_user(
            email="designer@example.com",
            password=self.password,
            full_name="Test Designer",
            role=User.Role.DESIGNER,
        )

    def test_login_requires_email_and_password(self):
        response = self.client.post(reverse("accounts:login"), {})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_login_success_redirects_to_dashboard(self):
        response = self.client.post(reverse("accounts:login"), {
            "email": self.user.email,
            "password": self.password,
        })
        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertEqual(self.user.login_journal.count(), 1)
        self.assertEqual(self.user.login_journal.first().status, "success")

    def test_login_wrong_password_logs_failure(self):
        response = self.client.post(reverse("accounts:login"), {
            "email": self.user.email,
            "password": "wrong-password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.login_journal.filter(status="failed").count(), 1)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_two_factor_login_requires_challenge(self):
        secret = pyotp.random_base32()
        self.user.totp_secret = secret
        self.user.two_factor_enabled = True
        self.user.save()

        response = self.client.post(reverse("accounts:login"), {
            "email": self.user.email,
            "password": self.password,
        })
        self.assertRedirects(response, reverse("accounts:2fa_challenge"))

        code = pyotp.TOTP(secret).now()
        response = self.client.post(reverse("accounts:2fa_challenge"), {"code": code})
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_notification_preference_auto_created(self):
        self.assertTrue(hasattr(self.user, "notification_preference"))


class RegisterFormTests(TestCase):
    def test_register_creates_user(self):
        response = self.client.post(reverse("accounts:register"), {
            "email": "new.designer@example.com",
            "full_name": "New Designer",
            "role": User.Role.DESIGNER,
            "password1": "s3curePass!23",
            "password2": "s3curePass!23",
        })
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertTrue(User.objects.filter(email="new.designer@example.com").exists())
