from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User

from .models import Project, ProjectMember


class ProjectVisibilityTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN)
        self.designer = User.objects.create_user(email="designer@example.com", password="pw12345!", full_name="Designer", role=User.Role.DESIGNER)
        self.outsider = User.objects.create_user(email="outsider@example.com", password="pw12345!", full_name="Outsider", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="Visible to member", created_by=self.admin)
        ProjectMember.objects.create(project=self.project, user=self.designer)

    def test_admin_sees_all_projects(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("projects:list"))
        self.assertContains(response, "Visible to member")

    def test_member_sees_their_project(self):
        self.client.force_login(self.designer)
        response = self.client.get(reverse("projects:list"))
        self.assertContains(response, "Visible to member")

    def test_non_member_does_not_see_project(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("projects:list"))
        self.assertNotContains(response, "Visible to member")

    def test_non_member_gets_403_on_detail(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("projects:detail", args=[self.project.pk]))
        self.assertEqual(response.status_code, 403)

    def test_designer_cannot_create_project(self):
        self.client.force_login(self.designer)
        response = self.client.get(reverse("projects:create"))
        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_project(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("projects:create"), {
            "name": "New project", "stage": "concept", "status": "active",
            "budget": 1000, "paid_amount": 0,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Project.objects.filter(name="New project").exists())

    def test_non_member_without_can_edit_cannot_edit(self):
        ProjectMember.objects.filter(project=self.project, user=self.designer).update(can_edit=False)
        self.client.force_login(self.designer)
        response = self.client.get(reverse("projects:update", args=[self.project.pk]))
        self.assertEqual(response.status_code, 403)
