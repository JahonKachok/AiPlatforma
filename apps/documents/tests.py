import io
import shutil
import tempfile
import zipfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import Discipline, User
from apps.notifications.models import Notification
from apps.projects.models import Project, ProjectMember, Section, SubObject, SubObjectDiscipline

from .models import ApprovalStage, ApprovalStatus, AuditLog, Document, DocumentStatus, DocumentVersion


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

    def test_view_only_member_cannot_delete_someone_elses_document(self):
        ProjectMember.objects.filter(project=self.project, user=self.reviewer1).update(can_edit=False)
        self.client.force_login(self.reviewer1)
        response = self.client.post(reverse("documents:delete", args=[self.document.pk]))
        self.assertEqual(response.status_code, 403)
        self.client.post(reverse("documents:list"), {"delete_selected": "1", "selected": [self.document.pk]})
        self.assertTrue(Document.objects.filter(pk=self.document.pk).exists())

    def test_uploader_cannot_route_their_own_document(self):
        """Aks holda o'zini tekshiruvchi qilib, o'z hujjatini tasdiqlardi."""
        ProjectMember.objects.filter(project=self.project, user=self.uploader).update(can_edit=False)
        self.client.force_login(self.uploader)
        response = self.client.get(reverse("documents:assign_stages", args=[self.document.pk]))
        self.assertEqual(response.status_code, 403)

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


_TMP_MEDIA = tempfile.mkdtemp(prefix="docs-test-")


@override_settings(MEDIA_ROOT=_TMP_MEDIA)
class LocationZipTelegramTests(TestCase):
    """Hujjat joylashuvi (obyekt/intizom), ZIP yuklash va Telegram'ga ulashish."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(email="u@example.com", password="pw12345!", full_name="Ali Valiyev", role=User.Role.DESIGNER, telegram_chat_id="111")
        self.boss = User.objects.create_user(email="b@example.com", password="pw12345!", full_name="Boss", role=User.Role.MANAGER, telegram_chat_id="222")
        self.outsider = User.objects.create_user(email="o@example.com", password="pw12345!", full_name="Outsider", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="Zavod", created_by=self.boss)
        ProjectMember.objects.create(project=self.project, user=self.user)
        self.ar, _ = Discipline.objects.get_or_create(code="AR", defaults={"name": "Arxitektura"})
        self.kj, _ = Discipline.objects.get_or_create(code="KJ", defaults={"name": "Konstruktiv"})
        self.obj = SubObject.objects.create(project=self.project, name="Bino 1")
        self.pod = SubObject.objects.create(project=self.project, parent=self.obj, name="Blok A")
        self.sec_ar = Section.objects.create(project=self.project, sub_object=self.pod, discipline=self.ar, name="AR")
        self.sec_kj = Section.objects.create(project=self.project, sub_object=self.obj, discipline=self.kj, name="KJ")
        self.dwg = self._doc("Plan", "plan 1-qavat.dwg", self.sec_ar)
        self.pdf = self._doc("Fasad", "fasad.pdf", self.sec_ar)
        self.kj_pdf = self._doc("Fundament", "fund.pdf", self.sec_kj)
        other = Project.objects.create(name="Yashirin", created_by=self.boss)
        self.hidden = Document.objects.create(name="Secret", project=other, uploaded_by=self.boss,
                                              file=SimpleUploadedFile("secret.pdf", b"x"), file_size=1)

    def _doc(self, name, filename, section, data=b"data"):
        return Document.objects.create(
            name=name, project=self.project, section=section, uploaded_by=self.user,
            file=SimpleUploadedFile(filename, data), file_size=len(data),
        )

    def _zip_names(self, response):
        return sorted(zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content))).namelist())

    def test_list_shows_object_and_discipline(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("documents:list"))
        self.assertContains(response, "Bino 1 › Blok A")
        self.assertContains(response, "Zavod / Bino 1 / Blok A / AR")

    def test_filters_by_object_including_pods_discipline_and_kind(self):
        self.client.force_login(self.user)
        url = reverse("documents:list")
        page = self.client.get(url, {"project": self.project.pk, "sub_object": self.obj.pk})
        self.assertEqual(page.context["filtered_total"], 3)
        page = self.client.get(url, {"discipline": self.kj.pk})
        self.assertEqual([d.pk for d in page.context["page_obj"]], [self.kj_pdf.pk])
        page = self.client.get(url, {"kind": "dwg"})
        self.assertEqual([d.pk for d in page.context["page_obj"]], [self.dwg.pk])

    def test_zip_of_filtered_list_keeps_folders_and_names(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("documents:bulk_download"), {"all": "1", "discipline": self.ar.pk})
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn('filename="Zavod.zip"', response["Content-Disposition"])
        self.assertEqual(self._zip_names(response), ["Zavod/Bino 1/Blok A/AR/fasad.pdf", "Zavod/Bino 1/Blok A/AR/plan 1-qavat.dwg"])

    def test_zip_never_includes_invisible_documents(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("documents:bulk_download"), {"id": [self.hidden.pk, self.kj_pdf.pk]})
        self.assertEqual(self._zip_names(response), ["Zavod/Bino 1/KJ/fund.pdf"])

    def test_same_name_in_one_folder_is_not_overwritten(self):
        dup = self._doc("Plan copy", "plan 1-qavat.dwg", self.sec_ar)
        self.assertNotEqual(dup.file.name, self.dwg.file.name)  # omborda Django nomni o'zgartirdi
        self.client.force_login(self.user)
        response = self.client.get(reverse("documents:bulk_download"), {"id": [self.dwg.pk, dup.pk]})
        self.assertEqual(self._zip_names(response), [
            "Zavod/Bino 1/Blok A/AR/plan 1-qavat (2).dwg", "Zavod/Bino 1/Blok A/AR/plan 1-qavat.dwg",
        ])

    def test_single_download_keeps_original_name(self):
        self._doc("Plan copy", "plan 1-qavat.dwg", self.sec_ar)  # ombordagi nom endi boshqacha
        self.client.force_login(self.user)
        response = self.client.get(reverse("documents:download", args=[self.dwg.pk]))
        self.assertIn("plan 1-qavat.dwg", response["Content-Disposition"])

    @patch("apps.telegram_bot.services.send_document", return_value=True)
    def test_one_file_goes_to_telegram_as_is(self, send):
        self.client.force_login(self.user)
        self.client.post(reverse("documents:list"), {"send_telegram": "1", "recipient": self.boss.pk, "selected": [self.dwg.pk]})
        chat_id, _fh, filename, caption = send.call_args.args
        self.assertEqual((chat_id, filename), ("222", "plan 1-qavat.dwg"))
        self.assertIn("Plan", caption)
        self.assertTrue(AuditLog.objects.filter(action="sent_telegram", object_id=str(self.dwg.pk)).exists())

    @patch("apps.telegram_bot.services.send_document", return_value=True)
    def test_several_files_go_as_one_zip(self, send):
        self.client.force_login(self.user)
        self.client.post(reverse("documents:list"), {"send_telegram": "1", "selected": [self.dwg.pk, self.kj_pdf.pk, self.hidden.pk]})
        chat_id, _fh, filename, _caption = send.call_args.args
        self.assertEqual((chat_id, filename), ("111", "Zavod.zip"))  # qabul qiluvchi ko'rsatilmasa — o'zi
        self.assertEqual(AuditLog.objects.filter(action="sent_telegram").count(), 2)  # yashirin hujjat tushib qoldi

    @patch("apps.telegram_bot.services.send_document", return_value=True)
    def test_too_large_file_is_reported_not_sent(self, send):
        Document.objects.filter(pk=self.dwg.pk).update(file_size=60 * 1024 * 1024)
        self.client.force_login(self.user)
        self.client.post(reverse("documents:list"), {"send_telegram": "1", "selected": [self.dwg.pk]})
        send.assert_not_called()
        self.assertTrue(Notification.objects.filter(user=self.user, type="document").exists())

    @patch("apps.telegram_bot.services.send_document", return_value=True)
    def test_recipient_without_telegram_is_refused(self, send):
        self.client.force_login(self.user)
        self.client.post(reverse("documents:list"), {"send_telegram": "1", "recipient": self.outsider.pk, "selected": [self.dwg.pk]})
        send.assert_not_called()


class FakeDrive:
    """Drive API o'rnini bosadi: papkalar va fayllar xotirada."""

    def __init__(self):
        self.folders = {}   # (parent, name) -> id
        self.files = {}     # id -> {"name", "parent", "data"}
        self.calls = []

    def ensure_folder(self, parent, name):
        self.calls.append(("ensure", parent, name))
        return self.folders.setdefault((parent, name), f"F{len(self.folders) + 1}")

    def upload(self, folder, name, fh, mime="", description=""):
        file_id = f"D{len(self.files) + 1}"
        self.files[file_id] = {"name": name, "parent": folder, "data": fh.read()}
        return file_id

    def move(self, file_id, new_parent, old_parent):
        assert self.files[file_id]["parent"] == old_parent
        self.files[file_id]["parent"] = new_parent

    def download(self, file_id):
        return io.BytesIO(self.files[file_id]["data"])

    def path_of(self, folder_id):
        names = {v: k for k, v in self.folders.items()}
        parts = []
        while folder_id in names:
            parent, name = names[folder_id]
            parts.insert(0, name)
            folder_id = parent
        return "/".join(parts)


@override_settings(MEDIA_ROOT=_TMP_MEDIA, GOOGLE_DRIVE_CREDENTIALS="{}", GOOGLE_DRIVE_ROOT_FOLDER_ID="ROOT")
class ArchivistDriveTests(TestCase):
    def setUp(self):
        from . import drive

        self.fake = FakeDrive()
        for name in ("ensure_folder", "upload", "move", "download"):
            patcher = patch.object(drive, name, getattr(self.fake, name))
            patcher.start()
            self.addCleanup(patcher.stop)
        self.user = User.objects.create_user(email="a@example.com", password="pw12345!", full_name="Archivist", role=User.Role.MANAGER)
        self.project = Project.objects.create(name="Zavod", created_by=self.user)
        self.ar, _ = Discipline.objects.get_or_create(code="AR", defaults={"name": "Arxitektura"})
        obj = SubObject.objects.create(project=self.project, name="Bino 1")
        self.section = Section.objects.create(project=self.project, sub_object=obj, discipline=self.ar, name="AR")

    def _upload(self, filename="plan.dwg", data=b"v1"):
        self.client.force_login(self.user)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("documents:upload"), {
                "name": "Plan", "project": self.project.pk, "section": self.section.pk, "version": "1.0",
                "file": SimpleUploadedFile(filename, data),
            })

    def test_upload_goes_to_project_object_discipline_folder(self):
        self._upload()
        document = Document.objects.get()
        version = document.versions.get()
        self.assertEqual((version.revision, version.drive_status), (1, "synced"))
        self.assertEqual(self.fake.path_of(document.drive_folder_id), "Zavod/Bino 1/AR")
        self.assertEqual(self.fake.files[document.drive_file_id]["name"], "plan.dwg")

    def test_same_name_becomes_next_revision_and_old_one_moves_to_old(self):
        self._upload(data=b"v1")
        self._upload(data=b"v2")
        document = Document.objects.get()  # dublikat hujjat yaratilmadi
        rev1, rev2 = document.versions.order_by("revision")
        self.assertEqual((rev1.revision, rev2.revision, document.version), (1, 2, "1.1"))
        self.assertTrue(rev1.in_old_folder)
        self.assertEqual(self.fake.path_of(self.fake.files[rev1.drive_file_id]["parent"]), "Zavod/Bino 1/AR/Old")
        self.assertEqual(self.fake.files[document.drive_file_id]["data"], b"v2")
        self.assertEqual(self.fake.files[document.drive_file_id]["parent"], document.drive_folder_id)

    def test_folders_are_cached(self):
        self._upload("a.dwg")
        before = len(self.fake.calls)
        self._upload("b.dwg")
        self.assertEqual(len(self.fake.calls), before)

    def test_drive_error_is_recorded_and_retried_later(self):
        from . import drive
        from .tasks import sync_pending_to_drive

        with patch.object(drive, "upload", side_effect=drive.DriveError("Drive API 403: no quota")):
            self._upload()
        version = DocumentVersion.objects.get()
        self.assertEqual(version.drive_status, "error")
        self.assertIn("403", version.drive_error)
        self.assertEqual(sync_pending_to_drive(), 1)
        version.refresh_from_db()
        self.assertEqual(version.drive_status, "synced")

    def test_without_drive_config_nothing_is_uploaded(self):
        with self.settings(GOOGLE_DRIVE_CREDENTIALS=""):
            self._upload()
        self.assertEqual(DocumentVersion.objects.get().drive_status, "pending")
        self.assertEqual(self.fake.files, {})

    def test_deleted_local_copy_is_read_from_drive(self):
        with self.settings(GOOGLE_DRIVE_DELETE_LOCAL="1"):
            self._upload(data=b"content")
        document = Document.objects.get()
        self.assertFalse(document.file.storage.exists(document.file.name))
        response = self.client.get(reverse("documents:download", args=[document.pk]))
        self.assertEqual(b"".join(response.streaming_content), b"content")

    def test_ai_tool_sends_object_zip_to_colleague(self):
        from apps.ai_agents.agent_tools import build_telegram_tools

        User.objects.create_user(email="c@example.com", password="pw12345!", full_name="Karim Aliyev", role=User.Role.DESIGNER, telegram_chat_id="333")
        self._upload("a.dwg")
        self._upload("b.pdf")
        tool = {t.__name__: t for t in build_telegram_tools(self.user)}["send_documents_zip"]
        with patch("apps.telegram_bot.services.send_document", return_value=True) as send:
            answer = tool("Zavod", recipient_name="Karim", object_name="Bino 1", discipline_code="ar")
        self.assertIn("2", answer)
        chat_id, _fh, filename, _caption = send.call_args.args
        self.assertEqual((chat_id, filename), ("333", "Zavod.zip"))


class DriveCredentialsSettingTests(TestCase):
    def test_service_account_json_is_validated(self):
        from apps.core.admin_ops import _validate_integration

        self.assertIsNotNone(_validate_integration("GOOGLE_DRIVE_CREDENTIALS", "not json"))
        self.assertIsNotNone(_validate_integration("GOOGLE_DRIVE_CREDENTIALS", '{"type": "user"}'))
        key = '{"type": "service_account", "client_email": "x@y.iam.gserviceaccount.com", "private_key": "-----BEGIN"}'
        self.assertIsNone(_validate_integration("GOOGLE_DRIVE_CREDENTIALS", key))
