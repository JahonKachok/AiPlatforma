import pyotp
from django.core.cache import cache
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
            "password1": "s3curePass!23",
            "password2": "s3curePass!23",
        })
        self.assertRedirects(response, reverse("accounts:login"))
        self.assertTrue(User.objects.filter(email="new.designer@example.com").exists())

    def test_register_cannot_choose_its_own_role(self):
        """Ochiq ro'yxatdan o'tishda rol yuborilsa ham e'tiborga olinmasligi
        kerak — aks holda har kim o'zini admin qilib yozdirib, hamma loyiha va
        moliyaviy ma'lumotlarga kirish huquqini olardi."""
        response = self.client.post(reverse("accounts:register"), {
            "email": "attacker@example.com",
            "full_name": "Attacker",
            "role": User.Role.ADMIN,
            "is_superuser": "on",
            "is_staff": "on",
            "password1": "s3curePass!23",
            "password2": "s3curePass!23",
        })
        self.assertRedirects(response, reverse("accounts:login"))
        user = User.objects.get(email="attacker@example.com")
        self.assertEqual(user.role, User.Role.DESIGNER)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_register_normalizes_email_case(self):
        User.objects.create_user(email="taken@example.com", password="s3curePass!23", full_name="Taken")
        response = self.client.post(reverse("accounts:register"), {
            "email": "Taken@Example.com",
            "full_name": "Duplicate",
            "password1": "s3curePass!23",
            "password2": "s3curePass!23",
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)


class BruteForceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.password = "s3curePass!23"
        self.user = User.objects.create_user(
            email="target@example.com", password=self.password, full_name="Target",
        )

    def tearDown(self):
        cache.clear()

    def test_login_locks_out_after_repeated_failures(self):
        from .views import LOGIN_ATTEMPT_LIMIT

        for _ in range(LOGIN_ATTEMPT_LIMIT):
            self.client.post(reverse("accounts:login"), {
                "email": self.user.email, "password": "wrong",
            })
        # To'g'ri parol ham blok muddati tugagunicha o'tmasligi kerak.
        response = self.client.post(reverse("accounts:login"), {
            "email": self.user.email, "password": self.password,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_successful_login_resets_the_counter(self):
        self.client.post(reverse("accounts:login"), {
            "email": self.user.email, "password": "wrong",
        })
        self.client.post(reverse("accounts:login"), {
            "email": self.user.email, "password": self.password,
        })
        from .views import _attempt_key

        self.assertIsNone(cache.get(_attempt_key(self.user.email)))


class LogoutTests(TestCase):
    def test_logout_rejects_get(self):
        """GET bilan chiqarib yuborish CSRF hisoblanadi (<img src=...>)."""
        user = User.objects.create_user(
            email="logout@example.com", password="s3curePass!23", full_name="Logout",
        )
        self.client.force_login(user)
        response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(self.client.session.get("_auth_user_id"))
