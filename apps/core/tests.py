from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

from .json_utils import script_json


class ScriptJsonTests(TestCase):
    def test_closing_script_tag_is_escaped(self):
        """Shablonlarda bu JSON <script> ichida |safe bilan chiqariladi, ya'ni
        ma'lumot ichidagi </script> saqlanuvchi XSS bergan bo'lardi."""
        payload = script_json({"name": "</script><img src=x onerror=alert(1)>"})
        self.assertNotIn("<", payload)
        self.assertNotIn(">", payload)
        self.assertIn("\\u003C/script\\u003E", payload)


class DarkModeRedirectTests(TestCase):
    def test_external_next_is_ignored(self):
        """?next= tashqi saytga ishora qilsa, ochiq redirect bo'lmasligi kerak."""
        response = self.client.post(reverse("core:set_dark_mode"), {
            "dark_mode": "1", "next": "https://evil.example/steal",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    def test_local_next_is_kept(self):
        response = self.client.post(reverse("core:set_dark_mode"), {
            "dark_mode": "0", "next": "/projects/",
        })
        self.assertEqual(response.url, "/projects/")


class ProtectedMediaTests(TestCase):
    def test_media_requires_login(self):
        """Yuklangan hujjatlar ilgari nginx orqali ochiq tarqatilardi."""
        response = self.client.get("/media/documents/2026/01/smeta.pdf")
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_missing_file_is_404_for_authenticated_user(self):
        user = User.objects.create_user(
            email="media@example.com", password="s3curePass!23", full_name="Media",
        )
        self.client.force_login(user)
        response = self.client.get("/media/documents/2026/01/nope.pdf")
        self.assertEqual(response.status_code, 404)
