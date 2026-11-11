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

    def test_registered_account_waits_for_activation(self):
        """Ochiq ro'yxatdan o'tgan hisob admin faollashtirmaguncha kira olmaydi."""
        self.client.post(reverse("accounts:register"), {
            "email": "stranger@example.com",
            "full_name": "Stranger",
            "password1": "s3curePass!23",
            "password2": "s3curePass!23",
        })
        self.assertFalse(User.objects.get(email="stranger@example.com").is_active)
        response = self.client.post(reverse("accounts:login"), {
            "email": "stranger@example.com", "password": "s3curePass!23",
        })
        self.assertFalse(response.wsgi_request.user.is_authenticated)

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

    def test_one_ip_is_locked_out_across_many_accounts(self):
        """Ko'p hisobga bittadan parol sinash (password spraying)."""
        from .views import IP_ATTEMPT_LIMIT

        for i in range(IP_ATTEMPT_LIMIT):
            self.client.post(reverse("accounts:login"), {
                "email": f"nobody{i}@example.com", "password": "wrong",
            })
        response = self.client.post(reverse("accounts:login"), {
            "email": self.user.email, "password": self.password,
        })
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_totp_code_cannot_be_reused(self):
        secret = pyotp.random_base32()
        self.user.totp_secret = secret
        self.user.two_factor_enabled = True
        self.user.save()
        code = pyotp.TOTP(secret).now()

        for expected_login in (True, False):
            self.client.logout()
            self.client.post(reverse("accounts:login"), {
                "email": self.user.email, "password": self.password,
            })
            response = self.client.post(reverse("accounts:2fa_challenge"), {"code": code})
            self.assertEqual(response.wsgi_request.user.is_authenticated, expected_login)


class UserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="boss@example.com", password="pw12345!", full_name="Boss", role=User.Role.ADMIN,
        )
        self.manager = User.objects.create_user(
            email="manager@example.com", password="pw12345!", full_name="Manager", role=User.Role.MANAGER,
        )
        self.client.force_login(self.manager)

    def test_manager_cannot_promote_to_admin(self):
        self.client.post(reverse("accounts:user_update", args=[self.manager.pk]), {
            "full_name": "Manager", "role": User.Role.ADMIN, "is_active": "on",
        })
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.role, User.Role.MANAGER)

    def test_manager_cannot_create_an_admin(self):
        self.client.post(reverse("accounts:user_create"), {
            "email": "newadmin@example.com", "full_name": "New", "role": User.Role.ADMIN,
        })
        self.assertFalse(User.objects.filter(email="newadmin@example.com").exists())

    def test_manager_cannot_edit_an_admin(self):
        response = self.client.post(reverse("accounts:user_update", args=[self.admin.pk]), {
            "full_name": "Boss", "role": User.Role.DESIGNER,
        })
        self.assertEqual(response.status_code, 403)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, User.Role.ADMIN)
        self.assertTrue(self.admin.is_active)

    def test_admin_can_promote_to_admin(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_update", args=[self.manager.pk]), {
            "email": "manager@example.com", "full_name": "Manager", "role": User.Role.ADMIN, "is_active": "on",
        })
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.role, User.Role.ADMIN)

    def _create(self, **extra):
        data = {"email": "New.Worker@Example.com", "full_name": "New Worker", "role": User.Role.DESIGNER, **extra}
        return self.client.post(reverse("accounts:user_create"), data)

    def test_admin_creates_user_with_own_password(self):
        self.client.force_login(self.admin)
        self._create(password1="Strong-pass-2026", password2="Strong-pass-2026")
        user = User.objects.get(email="new.worker@example.com")
        self.assertTrue(user.check_password("Strong-pass-2026"))
        self.client.logout()
        self.assertTrue(self.client.login(username="new.worker@example.com", password="Strong-pass-2026"))

    def test_blank_password_generates_temporary_one(self):
        self.client.force_login(self.admin)
        self._create()
        user = User.objects.get(email="new.worker@example.com")
        self.assertTrue(user.has_usable_password())

    def test_create_rejects_mismatched_or_weak_password(self):
        self.client.force_login(self.admin)
        self._create(password1="Strong-pass-2026", password2="Other-pass-2026")
        self._create(password1="12345678", password2="12345678")
        self.assertFalse(User.objects.filter(email="new.worker@example.com").exists())

    def test_create_rejects_duplicate_email_in_other_case(self):
        self.client.force_login(self.admin)
        response = self._create(email="MANAGER@example.com")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(email__iexact="manager@example.com").count(), 1)

    def test_admin_changes_login_and_password(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_update", args=[self.manager.pk]), {
            "email": "Mgr@Example.com", "full_name": "Manager", "role": User.Role.MANAGER, "is_active": "on",
            "password1": "Fresh-pass-2026", "password2": "Fresh-pass-2026",
        })
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.email, "mgr@example.com")
        self.assertTrue(self.manager.check_password("Fresh-pass-2026"))

    def test_admin_edit_without_password_keeps_it(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_update", args=[self.manager.pk]), {
            "email": "manager@example.com", "full_name": "Manager 2", "role": User.Role.MANAGER, "is_active": "on",
        })
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.full_name, "Manager 2")
        self.assertTrue(self.manager.check_password("pw12345!"))

    def test_admin_changing_own_password_stays_signed_in(self):
        self.client.force_login(self.admin)
        self.client.post(reverse("accounts:user_update", args=[self.admin.pk]), {
            "email": "boss@example.com", "full_name": "Boss", "role": User.Role.ADMIN, "is_active": "on",
            "password1": "Fresh-pass-2026", "password2": "Fresh-pass-2026",
        })
        response = self.client.get(reverse("accounts:user_list"))
        self.assertEqual(response.status_code, 200)

    def test_manager_cannot_change_login_or_password(self):
        designer = User.objects.create_user(email="d@example.com", password="pw12345!", full_name="D")
        self.client.post(reverse("accounts:user_update", args=[designer.pk]), {
            "email": "hijack@example.com", "full_name": "D", "role": User.Role.DESIGNER, "is_active": "on",
            "password1": "Fresh-pass-2026", "password2": "Fresh-pass-2026",
        })
        designer.refresh_from_db()
        self.assertEqual(designer.email, "d@example.com")
        self.assertTrue(designer.check_password("pw12345!"))

    def test_django_admin_login_goes_through_the_app_login(self):
        """/django-admin/ ning o'z login sahifasi 2FA va cheklovni chetlab o'tardi."""
        self.client.logout()
        response = self.client.get("/django-admin/login/")
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)


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
