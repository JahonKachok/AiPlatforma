from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Discipline, User
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMember, Section, SubObject, SubObjectDiscipline

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

    def _review(self, user, stage, status, comment="Reviewed."):
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


class ApprovalSubmissionTests(TestCase):
    """The combined "send for approval" form: title/project/object/pod
    object/comment/file. Submission should auto-route to the object's GIP
    under the submitter's own discipline (АР -> ГИП), and approving it should
    push that discipline's progress on the sub-object to 100%."""

    def setUp(self):
        self.gip = User.objects.create_user(
            email="gip@example.com", password="pw12345!", full_name="Gip", role=User.Role.GIP,
        )
        self.architect = User.objects.create_user(
            email="architect2@example.com", password="pw12345!", full_name="Architect", role=User.Role.DESIGNER,
        )
        self.ar, _ = Discipline.objects.get_or_create(code="AR", defaults={"name": "Architecture"})
        self.architect.disciplines.add(self.ar)

        self.project = Project.objects.create(name="Submission project", created_by=self.gip)
        ProjectMember.objects.create(project=self.project, user=self.architect)
        self.building = SubObject.objects.create(project=self.project, name="Bino 1", gip=self.gip)
        self.assignment = SubObjectDiscipline.objects.create(
            sub_object=self.building, discipline=self.ar, weight=100, progress=0,
        )
        self.url = reverse("documents:submit_for_approval")

    def _submit(self, sub_object=None):
        self.client.force_login(self.architect)
        return self.client.post(self.url, {
            "title": "Facade drawings", "project": self.project.pk,
            "sub_object": (sub_object or self.building).pk,
            "comment": "First draft for review.",
            "file": SimpleUploadedFile("facade.pdf", b"data", content_type="application/pdf"),
        })

    def test_submitting_creates_a_single_stage_routed_to_the_gip(self):
        response = self._submit()
        self.assertEqual(response.status_code, 302)
        document = Document.objects.get(name="Facade drawings")
        self.assertEqual(document.status, DocumentStatus.REVIEW)
        self.assertEqual(document.section.discipline, self.ar)
        self.assertEqual(document.section.sub_object, self.building)
        stages = list(document.approval_stages.all())
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0].reviewer, self.gip)

    def test_submission_comment_is_kept_as_the_first_version_note(self):
        self._submit()
        document = Document.objects.get(name="Facade drawings")
        self.assertEqual(document.versions.first().notes, "First draft for review.")

    def test_approving_the_stage_sets_discipline_progress_to_100(self):
        self._submit()
        document = Document.objects.get(name="Facade drawings")
        stage = document.approval_stages.get()
        self.client.force_login(self.gip)
        self.client.post(reverse("documents:review_stage", args=[stage.pk]), {
            "status": "approved", "comment": "Looks good.",
        })
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.progress, 100)
        document.refresh_from_db()
        self.assertEqual(document.status, DocumentStatus.APPROVED)

    def test_user_without_the_discipline_cannot_submit(self):
        outsider = User.objects.create_user(
            email="outsider8@example.com", password="pw12345!", full_name="Outsider", role=User.Role.DESIGNER,
        )
        self.client.force_login(outsider)
        response = self.client.post(self.url, {
            "title": "Facade drawings", "project": self.project.pk, "sub_object": self.building.pk,
            "comment": "First draft.", "file": SimpleUploadedFile("f.pdf", b"d", content_type="application/pdf"),
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Document.objects.filter(name="Facade drawings").exists())

    def test_object_without_gip_cannot_be_submitted_to(self):
        no_gip_object = SubObject.objects.create(project=self.project, name="Bino 2")
        SubObjectDiscipline.objects.create(sub_object=no_gip_object, discipline=self.ar, weight=100)
        response = self._submit(sub_object=no_gip_object)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Document.objects.filter(name="Facade drawings").exists())
