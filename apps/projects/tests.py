from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Discipline, User

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

    def test_admin_can_delete_project_with_payment_requests(self):
        from apps.finance.models import Contractor, CostCode, PaymentRequest

        cost_code = CostCode.objects.create(project=self.project, code="03-30-00", category="Beton", budget=1000)
        contractor = Contractor.objects.create(name="ElektroServis LLC")
        PaymentRequest.objects.create(
            project=self.project, cost_code=cost_code, contractor=contractor,
            amount=123123, requested_by=self.admin,
        )
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

    def test_non_editor_gets_403(self):
        self.client.force_login(self.outsider)
        response = self.client.post(self.url, {
            f"weight_{self.assignment.pk}": "100", f"progress_{self.assignment.pk}": "42",
        })
        self.assertEqual(response.status_code, 403)
