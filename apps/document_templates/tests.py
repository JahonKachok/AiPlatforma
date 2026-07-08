from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.projects.models import Project, ProjectMember

from .models import DocumentTemplate


class TemplateAccessTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(email="manager@example.com", password="pw12345!", full_name="Manager", role=User.Role.MANAGER)
        self.designer = User.objects.create_user(email="designer@example.com", password="pw12345!", full_name="Designer", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="P1", created_by=self.manager, client_name="ACME", budget=1000)
        ProjectMember.objects.create(project=self.project, user=self.designer)
        self.template = DocumentTemplate.objects.create(
            name="Contract", content="Dear {{client_name}}, budget is {{budget}}.", created_by=self.manager,
        )

    def test_designer_cannot_create_template(self):
        self.client.force_login(self.designer)
        response = self.client.get(reverse("document_templates:create"))
        self.assertEqual(response.status_code, 403)

    def test_manager_can_create_template(self):
        self.client.force_login(self.manager)
        response = self.client.get(reverse("document_templates:create"))
        self.assertEqual(response.status_code, 200)

    def test_designer_can_generate_from_template(self):
        self.client.force_login(self.designer)
        response = self.client.post(reverse("document_templates:generate", args=[self.template.pk]), {
            "project": self.project.pk, "save_as_document": "on",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dear")

    def test_designer_cannot_delete_template(self):
        self.client.force_login(self.designer)
        response = self.client.get(reverse("document_templates:delete", args=[self.template.pk]))
        self.assertEqual(response.status_code, 403)
