from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.documents.models import AuditLog
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task

from .json_utils import script_json
from .templatetags.dashboard_extras import activity_label, activity_tone, sparkline_points


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


class DashboardDataTests(TestCase):
    """Every figure on the dashboard has to come out of the database, and only
    out of the rows the viewer is allowed to see."""

    def setUp(self):
        self.admin = User.objects.create_user(
            email="dashadmin@example.com", password="pw12345!", full_name="Dash Admin",
            role=User.Role.ADMIN,
        )
        self.designer = User.objects.create_user(
            email="dashdesigner@example.com", password="pw12345!", full_name="Dash Designer",
            role=User.Role.DESIGNER,
        )
        self.mine = Project.objects.create(
            name="Mine", created_by=self.admin, status=Project.Status.ACTIVE,
        )
        self.theirs = Project.objects.create(
            name="Theirs", created_by=self.admin, status=Project.Status.ACTIVE,
        )
        ProjectMember.objects.create(project=self.mine, user=self.designer)

    def _kpis(self, response):
        return {card["key"]: card for card in response.context["kpi_cards"]}

    def test_kpis_count_only_visible_projects(self):
        self.client.force_login(self.designer)
        kpis = self._kpis(self.client.get(reverse("core:dashboard")))
        self.assertEqual(kpis["projects"]["value"], 1)

        self.client.force_login(self.admin)
        kpis = self._kpis(self.client.get(reverse("core:dashboard")))
        self.assertEqual(kpis["projects"]["value"], 2)

    def test_task_kpis_are_derived_from_real_tasks(self):
        Task.objects.create(
            title="Running", project=self.mine, creator=self.admin,
            assignee=self.designer, status=Task.Status.IN_PROGRESS,
        )
        Task.objects.create(
            title="Late", project=self.mine, creator=self.admin,
            status=Task.Status.NEW, deadline=timezone.localdate() - timedelta(days=3),
        )
        self.client.force_login(self.designer)
        kpis = self._kpis(self.client.get(reverse("core:dashboard")))
        self.assertEqual(kpis["tasks"]["value"], 1)
        self.assertEqual(kpis["overdue"]["value"], 1)

    def test_every_kpi_exposes_a_real_sparkline_series(self):
        self.client.force_login(self.admin)
        for card in self.client.get(reverse("core:dashboard")).context["kpi_cards"]:
            self.assertIsInstance(card["spark"], list)
            self.assertEqual(len(card["spark"]), 8)
            self.assertTrue(all(isinstance(v, int) for v in card["spark"]))

    def test_activity_is_scoped_to_projects_the_user_can_see(self):
        AuditLog.log(obj=self.mine, action="updated", user=self.admin)
        AuditLog.log(obj=self.theirs, action="updated", user=self.admin)

        self.client.force_login(self.designer)
        entries = list(self.client.get(reverse("core:dashboard")).context["recent_activity"])
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].object_id, str(self.mine.pk))

    def test_admin_sees_activity_from_every_project(self):
        AuditLog.log(obj=self.mine, action="updated", user=self.admin)
        AuditLog.log(obj=self.theirs, action="updated", user=self.admin)

        self.client.force_login(self.admin)
        entries = list(self.client.get(reverse("core:dashboard")).context["recent_activity"])
        self.assertEqual(len(entries), 2)

    def test_team_lists_colleagues_from_visible_projects_only(self):
        colleague = User.objects.create_user(
            email="colleague@example.com", password="pw12345!", full_name="Colleague",
        )
        stranger = User.objects.create_user(
            email="stranger@example.com", password="pw12345!", full_name="Stranger",
        )
        ProjectMember.objects.create(project=self.mine, user=colleague)
        ProjectMember.objects.create(project=self.theirs, user=stranger)

        self.client.force_login(self.designer)
        team = list(self.client.get(reverse("core:dashboard")).context["team"])
        self.assertIn(colleague, team)
        self.assertNotIn(stranger, team)
        self.assertNotIn(self.designer, team)

    def test_ai_report_is_hidden_from_non_managers(self):
        from apps.ai_agents.models import AILog

        AILog.objects.create(agent="deadline", status=AILog.Status.SUCCESS, response="Report body")
        self.client.force_login(self.designer)
        self.assertIsNone(self.client.get(reverse("core:dashboard")).context["ai_report"])

        self.client.force_login(self.admin)
        self.assertIsNotNone(self.client.get(reverse("core:dashboard")).context["ai_report"])

    def test_new_badge_only_for_a_fresh_report(self):
        from apps.ai_agents.models import AILog

        log = AILog.objects.create(agent="deadline", status=AILog.Status.SUCCESS, response="Body")
        self.client.force_login(self.admin)
        self.assertTrue(self.client.get(reverse("core:dashboard")).context["ai_report_is_new"])

        AILog.objects.filter(pk=log.pk).update(created_at=timezone.now() - timedelta(days=5))
        self.assertFalse(self.client.get(reverse("core:dashboard")).context["ai_report_is_new"])

    def test_dashboard_renders_empty_states_without_data(self):
        lonely = User.objects.create_user(
            email="lonely@example.com", password="pw12345!", full_name="Lonely",
        )
        self.client.force_login(lonely)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "dsh-empty")
        for card in response.context["kpi_cards"]:
            self.assertEqual(card["value"], 0)

    def test_project_rows_carry_image_and_progress_fields(self):
        self.client.force_login(self.admin)
        for project in self.client.get(reverse("core:dashboard")).context["recent_projects"]:
            self.assertTrue(hasattr(project, "progress_value"))
            self.assertTrue(hasattr(project, "is_overdue"))
            self.assertTrue(hasattr(project, "image"))


class DashboardFilterTests(TestCase):
    def test_sparkline_needs_at_least_two_points(self):
        self.assertEqual(sparkline_points([]), "")
        self.assertEqual(sparkline_points([4]), "")

    def test_sparkline_maps_the_series_across_the_full_width(self):
        points = sparkline_points([0, 5]).split()
        self.assertEqual(len(points), 2)
        self.assertTrue(points[0].startswith("0.0,"))
        self.assertTrue(points[1].startswith("100.0,"))

    def test_flat_series_does_not_divide_by_zero(self):
        points = sparkline_points([3, 3, 3])
        self.assertEqual(len(points.split()), 3)

    def test_unknown_action_still_renders(self):
        self.assertEqual(activity_tone("something_new"), "blue")
        self.assertEqual(activity_label("something_new"), "something new")

    def test_known_actions_get_their_tone(self):
        self.assertEqual(activity_tone("deleted"), "red")
        self.assertEqual(activity_tone("created"), "green")
        self.assertEqual(activity_tone("status_changed"), "amber")


class WwwRedirectTests(TestCase):
    def test_www_is_redirected_to_the_bare_domain(self):
        with self.settings(ALLOWED_HOSTS=["example.com", "www.example.com"]):
            response = self.client.get("/accounts/login/?next=/projects/", HTTP_HOST="www.example.com")
        self.assertEqual(response.status_code, 301)
        self.assertEqual(response["Location"], "http://example.com/accounts/login/?next=/projects/")

    def test_https_scheme_is_kept(self):
        with self.settings(ALLOWED_HOSTS=["example.com", "www.example.com"]):
            response = self.client.get("/", HTTP_HOST="www.example.com", secure=True)
        self.assertEqual(response["Location"], "https://example.com/")

    def test_bare_domain_is_served_normally(self):
        with self.settings(ALLOWED_HOSTS=["example.com", "www.example.com"]):
            response = self.client.get("/accounts/login/", HTTP_HOST="example.com")
        self.assertEqual(response.status_code, 200)

    def test_unlisted_www_host_is_still_rejected(self):
        with self.settings(ALLOWED_HOSTS=["example.com"]):
            response = self.client.get("/", HTTP_HOST="www.evil.example")
        self.assertEqual(response.status_code, 400)
