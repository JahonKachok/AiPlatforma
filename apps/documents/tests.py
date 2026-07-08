from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMember

from .models import ApprovalStage, ApprovalStatus, Document, DocumentStatus


class ApprovalWorkflowTests(TestCase):
    def setUp(self):
        self.uploader = User.objects.create_user(email="uploader@example.com", password="pw12345!", full_name="Uploader", role=User.Role.DESIGNER)
        self.reviewer1 = User.objects.create_user(email="rev1@example.com", password="pw12345!", full_name="Reviewer One", role=User.Role.REVIEWER)
        self.reviewer2 = User.objects.create_user(email="rev2@example.com", password="pw12345!", full_name="Reviewer Two", role=User.Role.GIP)
        self.project = Project.objects.create(name="P1", created_by=self.uploader)
        for u in [self.uploader, self.reviewer1, self.reviewer2]:
            ProjectMember.objects.create(project=self.project, user=u)
        self.document = Document.objects.create(name="Doc.pdf", project=self.project, uploaded_by=self.uploader, status=DocumentStatus.REVIEW)
        self.stage1 = ApprovalStage.objects.create(document=self.document, stage_order=1, stage_name="First", reviewer=self.reviewer1)
        self.stage2 = ApprovalStage.objects.create(document=self.document, stage_order=2, stage_name="Second", reviewer=self.reviewer2)

    def _review(self, user, stage, status, comment=""):
        self.client.force_login(user)
        return self.client.post(reverse("documents:review_stage", args=[stage.pk]), {"status": status, "comment": comment})

    def test_only_assigned_reviewer_can_review(self):
        response = self._review(self.reviewer2, self.stage1, "approved")
        self.assertEqual(response.status_code, 403)

    def test_document_stays_in_review_until_all_stages_approved(self):
        self._review(self.reviewer1, self.stage1, "approved")
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.REVIEW)

        self._review(self.reviewer2, self.stage2, "approved")
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.APPROVED)

    def test_any_rejection_rejects_the_document(self):
        self._review(self.reviewer1, self.stage1, "rejected", comment="Not acceptable")
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.REJECTED)
        self.stage1.refresh_from_db()
        self.assertEqual(self.stage1.status, ApprovalStatus.REJECTED)

    def test_revision_sends_document_back_to_draft(self):
        self._review(self.reviewer1, self.stage1, "revision")
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, DocumentStatus.DRAFT)

    def test_cannot_review_same_stage_twice(self):
        self._review(self.reviewer1, self.stage1, "approved")
        response = self._review(self.reviewer1, self.stage1, "rejected")
        self.stage1.refresh_from_db()
        self.assertEqual(self.stage1.status, ApprovalStatus.APPROVED)
        self.assertRedirects(response, reverse("documents:detail", args=[self.document.pk]))

    def test_review_notifies_uploader(self):
        self._review(self.reviewer1, self.stage1, "rejected")
        self.assertTrue(Notification.objects.filter(user=self.uploader, type="approval").exists())
