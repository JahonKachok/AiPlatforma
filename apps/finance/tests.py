from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.projects.models import Project, ProjectMember

from .models import FinancialRecord


class FinanceRecordPermissionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email="admin@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN)
        self.designer = User.objects.create_user(email="designer@example.com", password="pw12345!", full_name="Designer", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="P1", created_by=self.admin)
        ProjectMember.objects.create(project=self.project, user=self.designer, can_edit=False)

    def test_non_editing_member_cannot_add_record(self):
        self.client.force_login(self.designer)
        response = self.client.post(reverse("finance:add_record", args=[self.project.pk]), {
            "type": "income", "amount": 100, "date": "2026-01-01", "status": "pending",
        })
        self.assertEqual(response.status_code, 403)
        self.assertEqual(FinancialRecord.objects.count(), 0)

    def test_admin_can_add_record(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("finance:add_record", args=[self.project.pk]), {
            "type": "income", "amount": 100, "currency": "UZS", "date": "2026-01-01", "status": "pending",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(FinancialRecord.objects.count(), 1)
