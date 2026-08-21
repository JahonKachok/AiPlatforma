import io
import zipfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from apps.accounts.models import Discipline, User
from apps.documents.models import Document

from .models import Project, ProjectMember, SubObject, SubObjectDiscipline


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
            "budget": 1000, "paid_amount": 0, "currency": "UZS",
            "construction_type": "new", "sector": "Housing", "object_type": "Category II",
            "funding_source": "own_funds", "region": "tashkent_city", "district": "Yunusobod",
            "address": "Test address 1",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Project.objects.filter(name="New project").exists())

    def test_non_member_without_can_edit_cannot_edit(self):
        ProjectMember.objects.filter(project=self.project, user=self.designer).update(can_edit=False)
        self.client.force_login(self.designer)
        response = self.client.get(reverse("projects:update", args=[self.project.pk]))
        self.assertEqual(response.status_code, 403)

    def test_edit_form_is_prefilled_with_existing_data(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("projects:update", args=[self.project.pk]))
        self.assertContains(response, 'value="Visible to member"')

    def test_saving_edit_form_continues_into_the_wizard(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse("projects:update", args=[self.project.pk]), {
            "name": "Visible to member", "stage": "concept", "status": "active",
            "budget": 1000, "paid_amount": 0, "currency": "UZS",
            "construction_type": "new", "sector": "Housing", "object_type": "Category II",
            "funding_source": "own_funds", "region": "tashkent_city", "district": "Yunusobod",
            "address": "Test address 1",
        })
        self.assertRedirects(response, reverse("projects:wizard_subobjects", args=[self.project.pk]))

    def test_admin_can_delete_project_with_employee_contracts(self):
        from apps.finance.models import EmployeeContract

        EmployeeContract.objects.create(user=self.admin, project=self.project, amount=123123)
        self.client.force_login(self.admin)
        response = self.client.post(reverse("projects:delete", args=[self.project.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())


class SubObjectProgressTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin2@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN,
        )
        self.designer = User.objects.create_user(
            email="designer2@example.com", password="pw12345!", full_name="Designer", role=User.Role.DESIGNER,
        )
        self.project = Project.objects.create(name="Housing complex", created_by=self.admin)
        ProjectMember.objects.create(project=self.project, user=self.designer, can_edit=False)

        self.ar, _ = Discipline.objects.get_or_create(code="AR", defaults={"name": "Architecture"})
        self.kr, _ = Discipline.objects.get_or_create(code="KR", defaults={"name": "Structural"})
        self.kj, _ = Discipline.objects.get_or_create(code="KJ", defaults={"name": "Steel structures"})

    def _sub_object(self, name, parent=None):
        return SubObject.objects.create(project=self.project, name=name, parent=parent)

    def _discipline(self, sub_object, discipline, weight, progress):
        return SubObjectDiscipline.objects.create(
            sub_object=sub_object, discipline=discipline, weight=weight, progress=progress,
        )

    def test_weighted_progress_of_leaf_sub_object(self):
        sub = self._sub_object("Sub-object 1")
        self._discipline(sub, self.ar, weight=40, progress=100)
        self._discipline(sub, self.kr, weight=30, progress=50)
        self._discipline(sub, self.kj, weight=30, progress=0)
        self.assertEqual(sub.progress, 55)

    def test_full_completion_is_100(self):
        sub = self._sub_object("Sub-object 1")
        self._discipline(sub, self.ar, weight=40, progress=100)
        self._discipline(sub, self.kr, weight=30, progress=100)
        self._discipline(sub, self.kj, weight=30, progress=100)
        self.assertEqual(sub.progress, 100)

    def test_invalid_weight_sum_returns_none(self):
        sub = self._sub_object("Sub-object 1")
        self._discipline(sub, self.ar, weight=40, progress=100)
        self._discipline(sub, self.kr, weight=30, progress=50)
        self._discipline(sub, self.kj, weight=20, progress=0)
        self.assertIsNone(sub.progress)

    def test_no_disciplines_returns_none(self):
        sub = self._sub_object("Sub-object 1")
        self.assertIsNone(sub.progress)

    def test_object_progress_averages_pod_objects(self):
        obj = self._sub_object("Building 1")
        pod1 = self._sub_object("Sub-object 1", parent=obj)
        pod2 = self._sub_object("Sub-object 2", parent=obj)
        self._discipline(pod1, self.ar, weight=100, progress=100)
        self._discipline(pod2, self.ar, weight=100, progress=50)
        self.assertEqual(obj.progress, 75)

    def test_object_progress_skips_unresolved_pod_objects(self):
        obj = self._sub_object("Building 1")
        pod1 = self._sub_object("Sub-object 1", parent=obj)
        pod2 = self._sub_object("Sub-object 2", parent=obj)
        self._discipline(pod1, self.ar, weight=100, progress=100)
        self._discipline(pod2, self.ar, weight=40, progress=50)  # invalid sum -> None, skipped
        self.assertEqual(obj.progress, 100)

    def test_project_progress_averages_top_level_objects_only(self):
        obj1 = self._sub_object("Building 1")
        obj2 = self._sub_object("Building 2")
        self._discipline(obj1, self.ar, weight=100, progress=100)
        self._discipline(obj2, self.ar, weight=100, progress=50)
        self.assertEqual(self.project.progress, 75)

    def test_project_progress_none_when_no_objects(self):
        self.assertIsNone(self.project.progress)


class DisciplineWeightsSaveViewTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin3@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN,
        )
        self.outsider = User.objects.create_user(
            email="outsider3@example.com", password="pw12345!", full_name="Outsider", role=User.Role.DESIGNER,
        )
        self.project = Project.objects.create(name="Office tower", created_by=self.admin)
        self.discipline, _ = Discipline.objects.get_or_create(code="AR", defaults={"name": "Architecture"})
        self.sub_object = SubObject.objects.create(project=self.project, name="Sub-object 1")
        self.assignment = SubObjectDiscipline.objects.create(
            sub_object=self.sub_object, discipline=self.discipline, weight=10, progress=10,
        )
        self.url = reverse(
            "projects:wizard_discipline_weights_save", args=[self.project.pk, self.sub_object.pk],
        )

    def test_out_of_range_value_is_rejected_and_not_persisted(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {
            f"weight_{self.assignment.pk}": "150", f"progress_{self.assignment.pk}": "10",
        })
        self.assertEqual(response.status_code, 302)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.weight, 10)
        self.assertEqual(self.assignment.progress, 10)

    def test_weights_not_summing_to_100_still_saves(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {
            f"weight_{self.assignment.pk}": "40", f"progress_{self.assignment.pk}": "20",
        })
        self.assertEqual(response.status_code, 302)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.weight, 40)
        self.assertEqual(self.assignment.progress, 20)
        self.assertIsNone(self.sub_object.progress)  # sum != 100, still unresolved

    def test_valid_full_weight_saves_and_resolves_progress(self):
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {
            f"weight_{self.assignment.pk}": "100", f"progress_{self.assignment.pk}": "42",
        })
        self.assertEqual(response.status_code, 302)
        self.assignment.refresh_from_db()
        self.assertEqual(self.sub_object.progress, 42)

    def test_weight_only_submission_leaves_progress_untouched(self):
        # The wizard step no longer collects progress at all — only a weight_<pk> field is
        # posted. Progress must be left exactly as it was, not reset to 0.
        self.client.force_login(self.admin)
        response = self.client.post(self.url, {f"weight_{self.assignment.pk}": "55"})
        self.assertEqual(response.status_code, 302)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.weight, 55)
        self.assertEqual(self.assignment.progress, 10)  # unchanged from setUp

    def test_non_editor_gets_403(self):
        self.client.force_login(self.outsider)
        response = self.client.post(self.url, {
            f"weight_{self.assignment.pk}": "100", f"progress_{self.assignment.pk}": "42",
        })
        self.assertEqual(response.status_code, 403)

    def test_save_and_continue_also_persists_pending_weight_edits(self):
        # Regression test: clicking "Save and continue" at the bottom of the wizard used to
        # submit a form with no weight_/progress_ fields at all, silently discarding whatever
        # the user had just typed into the weights table above.
        self.client.force_login(self.admin)
        wizard_url = reverse("projects:wizard_disciplines", args=[self.project.pk])
        response = self.client.post(wizard_url, {
            "target_id": str(self.sub_object.pk),
            f"weight_{self.assignment.pk}": "100", f"progress_{self.assignment.pk}": "77",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("projects:wizard_documents", args=[self.project.pk]))
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.weight, 100)
        self.assertEqual(self.assignment.progress, 77)

    def test_save_and_continue_without_weight_fields_still_advances(self):
        # No sub-object selected on the page (or no edits made): should just advance as before.
        self.client.force_login(self.admin)
        wizard_url = reverse("projects:wizard_disciplines", args=[self.project.pk])
        response = self.client.post(wizard_url, {})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("projects:wizard_documents", args=[self.project.pk]))
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.weight, 10)  # unchanged


class WizardDocumentUploadTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin4@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN,
        )
        self.project = Project.objects.create(name="Docs project", created_by=self.admin)
        self.url = reverse("projects:wizard_document_upload", args=[self.project.pk])

    def test_uploading_several_files_at_once_keeps_all_of_them(self):
        self.client.force_login(self.admin)
        files = [
            SimpleUploadedFile("photo1.pdf", b"a", content_type="application/pdf"),
            SimpleUploadedFile("photo2.pdf", b"b", content_type="application/pdf"),
        ]
        response = self.client.post(self.url, {"doc_type": "photo_video", "file": files})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["documents"]), 2)
        self.assertEqual(
            Document.objects.filter(project=self.project, doc_type="photo_video").count(), 2,
        )

    def test_uploading_again_does_not_delete_previous_files(self):
        self.client.force_login(self.admin)
        self.client.post(self.url, {
            "doc_type": "photo_video",
            "file": [SimpleUploadedFile("photo1.pdf", b"a", content_type="application/pdf")],
        })
        self.client.post(self.url, {
            "doc_type": "photo_video",
            "file": [SimpleUploadedFile("photo2.pdf", b"b", content_type="application/pdf")],
        })
        self.assertEqual(
            Document.objects.filter(project=self.project, doc_type="photo_video").count(), 2,
        )

    def test_invalid_extension_rejects_whole_batch(self):
        self.client.force_login(self.admin)
        files = [
            SimpleUploadedFile("ok.pdf", b"a", content_type="application/pdf"),
            SimpleUploadedFile("bad.exe", b"b", content_type="application/octet-stream"),
        ]
        response = self.client.post(self.url, {"doc_type": "photo_video", "file": files})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Document.objects.filter(project=self.project).count(), 0)


class ProjectTeamMembershipTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin5@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN,
        )
        self.designer = User.objects.create_user(
            email="designer5@example.com", password="pw12345!", full_name="Designer", role=User.Role.DESIGNER,
        )
        self.project = Project.objects.create(name="Team project", created_by=self.admin)
        self.member = ProjectMember.objects.create(project=self.project, user=self.designer)

    def test_editor_can_remove_a_team_member(self):
        self.client.force_login(self.admin)
        url = reverse("projects:remove_member", args=[self.project.pk, self.designer.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            ProjectMember.objects.filter(project=self.project, user=self.designer).exists(),
        )

    def test_non_editor_cannot_remove_a_team_member(self):
        outsider = User.objects.create_user(
            email="outsider5@example.com", password="pw12345!", full_name="Outsider", role=User.Role.DESIGNER,
        )
        self.client.force_login(outsider)
        url = reverse("projects:remove_member", args=[self.project.pk, self.designer.pk])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            ProjectMember.objects.filter(project=self.project, user=self.designer).exists(),
        )


def _xlsx_upload(rows, filename="import.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.append(["Object", "Pod object"])
    for row in rows:
        ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return SimpleUploadedFile(
        filename, buffer.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


class SubObjectsExcelImportTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin6@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN,
        )
        self.project = Project.objects.create(name="Import project", created_by=self.admin)
        self.url = reverse("projects:wizard_subobjects_import", args=[self.project.pk])

    def test_template_download_works(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse("projects:wizard_subobjects_import_template", args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_import_creates_objects_and_pod_objects(self):
        self.client.force_login(self.admin)
        upload = _xlsx_upload([
            ["Bino 1", ""],
            ["", "KPP"],
            ["", "Garaj"],
            ["Bino 2", ""],
        ])
        response = self.client.post(self.url, {"file": upload})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SubObject.objects.filter(project=self.project, parent__isnull=True).count(), 2)
        bino1 = SubObject.objects.get(project=self.project, name="Bino 1")
        self.assertEqual(set(bino1.pod_objects.values_list("name", flat=True)), {"KPP", "Garaj"})

    def test_reimporting_does_not_duplicate(self):
        self.client.force_login(self.admin)
        upload1 = _xlsx_upload([["Bino 1", ""], ["", "KPP"]])
        self.client.post(self.url, {"file": upload1})
        upload2 = _xlsx_upload([["Bino 1", ""], ["", "KPP"]])
        self.client.post(self.url, {"file": upload2})
        self.assertEqual(SubObject.objects.filter(project=self.project, parent__isnull=True).count(), 1)
        self.assertEqual(SubObject.objects.filter(project=self.project, name="KPP").count(), 1)

    def test_pod_row_without_preceding_object_is_rejected(self):
        self.client.force_login(self.admin)
        upload = _xlsx_upload([["", "KPP"]])
        response = self.client.post(self.url, {"file": upload})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SubObject.objects.filter(project=self.project).exists())

    def test_non_editor_cannot_import(self):
        outsider = User.objects.create_user(
            email="outsider6@example.com", password="pw12345!", full_name="Outsider", role=User.Role.DESIGNER,
        )
        self.client.force_login(outsider)
        upload = _xlsx_upload([["Bino 1", ""]])
        response = self.client.post(self.url, {"file": upload})
        self.assertEqual(response.status_code, 403)


class DocumentsDownloadZipTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin7@example.com", password="pw12345!", full_name="Admin", role=User.Role.ADMIN,
        )
        self.project = Project.objects.create(name="Zip project", created_by=self.admin)
        self.url = reverse("projects:documents_download_zip", args=[self.project.pk])

    def test_downloads_a_zip_containing_uploaded_documents(self):
        self.client.force_login(self.admin)
        upload_url = reverse("projects:wizard_document_upload", args=[self.project.pk])
        self.client.post(upload_url, {
            "doc_type": "tz",
            "file": [SimpleUploadedFile("tz.pdf", b"hello", content_type="application/pdf")],
        })
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/zip")
        archive = zipfile.ZipFile(io.BytesIO(response.content))
        expected_path = "10_ТЭ/tz.pdf"
        self.assertEqual(archive.namelist(), [expected_path])
        self.assertEqual(archive.read(expected_path), b"hello")

    def test_no_documents_redirects_with_message(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_user_without_visibility_gets_403(self):
        outsider = User.objects.create_user(
            email="outsider7@example.com", password="pw12345!", full_name="Outsider", role=User.Role.DESIGNER,
        )
        self.client.force_login(outsider)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
