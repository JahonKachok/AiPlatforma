import json

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Discipline, User
from apps.projects.models import Project, ProjectMember, Section, SubObject

from .models import Task, TaskComment


class TaskFlowTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(email="creator@example.com", password="pw12345!", full_name="Creator", role=User.Role.MANAGER)
        self.assignee = User.objects.create_user(email="assignee@example.com", password="pw12345!", full_name="Assignee", role=User.Role.DESIGNER)
        self.other = User.objects.create_user(email="other@example.com", password="pw12345!", full_name="Other", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="P1", created_by=self.creator)
        for u in [self.creator, self.assignee, self.other]:
            ProjectMember.objects.create(project=self.project, user=u)
        self.task = Task.objects.create(title="Do the thing", project=self.project, assignee=self.assignee, creator=self.creator)

    def test_kanban_status_update(self):
        self.client.force_login(self.assignee)
        response = self.client.post(reverse("tasks:update_status", args=[self.task.pk]), {"status": "in_progress"})
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "in_progress")

    def test_invalid_status_is_ignored(self):
        self.client.force_login(self.assignee)
        self.client.post(reverse("tasks:update_status", args=[self.task.pk]), {"status": "not_a_status"})
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "new")

    def test_comment_owner_can_delete(self):
        comment = TaskComment.objects.create(task=self.task, user=self.assignee, content="hi")
        self.client.force_login(self.assignee)
        self.client.post(reverse("tasks:delete_comment", args=[self.task.pk, comment.pk]))
        self.assertFalse(TaskComment.objects.filter(pk=comment.pk).exists())

    def test_non_owner_cannot_delete_comment(self):
        comment = TaskComment.objects.create(task=self.task, user=self.assignee, content="hi")
        self.client.force_login(self.other)
        response = self.client.post(reverse("tasks:delete_comment", args=[self.task.pk, comment.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(TaskComment.objects.filter(pk=comment.pk).exists())

    def test_comment_delete_rejects_get(self):
        """GET bilan o'chirib bo'lmasligi kerak — aks holda <img src=...>
        joylab CSRF orqali izohlarni o'chirtirish mumkin edi."""
        comment = TaskComment.objects.create(task=self.task, user=self.assignee, content="hi")
        self.client.force_login(self.assignee)
        response = self.client.get(reverse("tasks:delete_comment", args=[self.task.pk, comment.pk]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(TaskComment.objects.filter(pk=comment.pk).exists())

    def test_plain_member_cannot_delete_or_edit_the_task(self):
        """Loyihani faqat ko'ra oladigan a'zo boshqalarning vazifasini o'chira olmaydi."""
        ProjectMember.objects.filter(project=self.project, user=self.other).update(can_edit=False)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(reverse("tasks:delete", args=[self.task.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse("tasks:update", args=[self.task.pk])).status_code, 403)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_creator_can_delete_the_task(self):
        self.client.force_login(self.creator)
        self.client.post(reverse("tasks:delete", args=[self.task.pk]))
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())

    def test_task_hidden_from_non_project_member(self):
        outsider = User.objects.create_user(email="outsider2@example.com", password="pw12345!", full_name="Outsider", role=User.Role.DESIGNER)
        self.client.force_login(outsider)
        response = self.client.get(reverse("tasks:detail", args=[self.task.pk]))
        self.assertEqual(response.status_code, 404)


class TaskAssignmentGrantsProjectVisibilityTests(TestCase):
    """Assigning a task to someone who isn't a project member yet should
    implicitly grant them at least view access — otherwise they couldn't see
    the work they were just assigned (a real bug this locks in against)."""

    def setUp(self):
        self.manager = User.objects.create_user(email="mgr@example.com", password="pw12345!", full_name="Manager", role=User.Role.MANAGER)
        self.newcomer = User.objects.create_user(email="newcomer@example.com", password="pw12345!", full_name="Newcomer", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="Fresh project", created_by=self.manager)

    def test_assigning_task_adds_assignee_as_project_member(self):
        self.assertFalse(ProjectMember.objects.filter(project=self.project, user=self.newcomer).exists())

        self.client.force_login(self.manager)
        self.client.post(reverse("tasks:create"), {
            "title": "Do the new thing", "project": self.project.pk, "assignee": self.newcomer.pk,
            "status": "new", "priority": "medium",
        })

        self.assertTrue(ProjectMember.objects.filter(project=self.project, user=self.newcomer).exists())

        self.client.force_login(self.newcomer)
        response = self.client.get(reverse("projects:detail", args=[self.project.pk]))
        self.assertEqual(response.status_code, 200)


class TaskFormCascadeTests(TestCase):
    """The create/edit form's Project -> Object -> Pod object -> Section cascade,
    and the Assignee list narrowing to employees who actually have the selected
    section's discipline (e.g. only architects once an AR section is picked),
    are driven by a JSON blob injected into the page. Lock in its shape."""

    def setUp(self):
        self.manager = User.objects.create_user(
            email="mgr2@example.com", password="pw12345!", full_name="Manager", role=User.Role.MANAGER,
        )
        self.architect = User.objects.create_user(
            email="architect@example.com", password="pw12345!", full_name="Architect", role=User.Role.DESIGNER,
        )
        self.engineer = User.objects.create_user(
            email="engineer@example.com", password="pw12345!", full_name="Engineer", role=User.Role.DESIGNER,
        )
        self.ar, _ = Discipline.objects.get_or_create(code="AR", defaults={"name": "Architecture"})
        self.kr, _ = Discipline.objects.get_or_create(code="KR", defaults={"name": "Structural"})
        self.architect.disciplines.add(self.ar)
        self.engineer.disciplines.add(self.kr)

        self.project = Project.objects.create(name="Cascade project", created_by=self.manager)
        self.building = SubObject.objects.create(project=self.project, name="Bino 1")
        self.pod = SubObject.objects.create(project=self.project, name="KPP", parent=self.building)
        self.section = Section.objects.create(
            project=self.project, sub_object=self.pod, discipline=self.ar, name="Arxitektura bo'limi",
        )

    def _cascade_data(self, response):
        marker = "window.TASK_FORM_CASCADE = "
        content = response.content.decode()
        start = content.index(marker) + len(marker)
        end = content.index(";</script>", start)
        return json.loads(content[start:end])

    def test_create_form_includes_cascade_data(self):
        # «Новая задача» endi Pult oynasida; cascade ma'lumoti tahrirlash formasida qoladi
        task = Task.objects.create(title="x", project=self.project, creator=self.manager)
        self.client.force_login(self.manager)
        response = self.client.get(reverse("tasks:update", args=[task.pk]))
        data = self._cascade_data(response)

        sub_object_ids = {so["id"] for so in data["subObjects"]}
        self.assertIn(str(self.building.pk), sub_object_ids)
        self.assertIn(str(self.pod.pk), sub_object_ids)
        pod_entry = next(so for so in data["subObjects"] if so["id"] == str(self.pod.pk))
        self.assertEqual(pod_entry["parent_id"], str(self.building.pk))

        section_entry = next(s for s in data["sections"] if s["id"] == str(self.section.pk))
        self.assertEqual(section_entry["sub_object_id"], str(self.pod.pk))
        self.assertEqual(section_entry["discipline_id"], str(self.ar.pk))

        ar_users = {u["id"] for u in data["disciplineUsers"][str(self.ar.pk)]}
        self.assertEqual(ar_users, {str(self.architect.pk)})
        kr_users = {u["id"] for u in data["disciplineUsers"][str(self.kr.pk)]}
        self.assertEqual(kr_users, {str(self.engineer.pk)})

    def test_edit_form_includes_cascade_data(self):
        task = Task.objects.create(
            title="Draw the facade", project=self.project, section=self.section,
            assignee=self.architect, creator=self.manager,
        )
        self.client.force_login(self.manager)
        response = self.client.get(reverse("tasks:update", args=[task.pk]))
        data = self._cascade_data(response)
        self.assertTrue(any(s["id"] == str(self.section.pk) for s in data["sections"]))


class TaskAssigneeFromCompositionTests(TestCase):
    """«Новая задача»: ijrochi faqat loyiha tarkibiga biriktirilganlardan."""

    def setUp(self):
        from apps.pult.models import PlanRow

        self.manager = User.objects.create_user(email="m3@example.com", password="pw12345!", full_name="Manager", role=User.Role.MANAGER)
        self.member = User.objects.create_user(email="in@example.com", password="pw12345!", full_name="Ali Valiev", role=User.Role.DESIGNER)
        self.outsider = User.objects.create_user(email="out@example.com", password="pw12345!", full_name="Outsider", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="Composition project", created_by=self.manager)
        PlanRow.objects.create(id=1, project=self.project, wbs="1.1", code="AR", name="AR", kind="Раздел", owner="Ali Valiev")

    def _post(self, assignee):
        self.client.force_login(self.manager)
        return self.client.post(reverse("tasks:create"), {
            "title": "Facade", "project": self.project.pk, "assignee": assignee.pk,
            "status": Task.Status.NEW, "priority": Task.Priority.MEDIUM,
        })

    def test_form_lists_composition_members(self):
        from .views import _task_form_cascade_json

        data = json.loads(_task_form_cascade_json(self.manager))
        self.assertEqual(data["projectMembers"][str(self.project.pk)], [str(self.member.pk)])

    def test_new_task_opens_the_pult_modal(self):
        self.client.force_login(self.manager)
        target = reverse("pult:section_work") + "?new=1"
        self.assertRedirects(self.client.get(reverse("tasks:create")), target, fetch_redirect_response=False)
        self.assertContains(self.client.get(reverse("tasks:board")), f'href="{target}"')
        self.assertContains(self.client.get(target), "?embed=1&amp;new=1#work")

    def test_member_can_be_assigned(self):
        self._post(self.member)
        self.assertTrue(Task.objects.filter(title="Facade", assignee=self.member).exists())

    def test_outsider_is_rejected(self):
        response = self._post(self.outsider)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Task.objects.filter(title="Facade").exists())


class TaskDetailPultFlowTests(TestCase):
    """Vazifa sahifasi Pult oqimi bilan yuradi: muddat → ish → hisobot → topshirish → qabul."""

    def setUp(self):
        from unittest import mock

        patcher = mock.patch("apps.notifications.tasks.send_notification_email.delay")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.gip = User.objects.create_user(email="gip-d@example.com", password="pw12345!", full_name="Gip", role=User.Role.GIP)
        self.worker = User.objects.create_user(email="worker-d@example.com", password="pw12345!", full_name="Worker", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="PD", created_by=self.gip)
        for u in (self.gip, self.worker):
            ProjectMember.objects.create(project=self.project, user=u)
        self.task = Task.objects.create(title="AR sheets", project=self.project, assignee=self.worker, creator=self.gip)
        self.detail = reverse("tasks:detail", args=[self.task.pk])
        self.action = reverse("tasks:pult_action", args=[self.task.pk])

    def act(self, user, action, **data):
        self.client.force_login(user)
        return self.client.post(self.action, {"action": action, **data})

    def status(self):
        self.task.workflow.refresh_from_db()
        return self.task.workflow.status

    def keys(self, user):
        self.client.force_login(user)
        response = self.client.get(self.detail)
        self.assertEqual(response.status_code, 200)
        return [a["key"] for a in response.context["card"]["actions"]]

    def test_full_cycle_from_detail_page(self):
        self.assertIn("accept_own", self.keys(self.worker))
        self.assertNotIn("approve_days", self.keys(self.worker))
        self.act(self.worker, "accept_own", days="5")
        self.assertEqual(self.status(), "На согласовании")
        self.assertIn("approve_days", self.keys(self.gip))
        self.act(self.gip, "approve_days")
        self.assertEqual(self.status(), "В работе")
        self.act(self.worker, "report", done="40", note="half of the sheets")
        self.task.workflow.refresh_from_db()
        self.assertAlmostEqual(self.task.workflow.done, 0.4)
        self.act(self.worker, "submit", src="on")
        self.assertEqual(self.status(), "На проверке")
        self.act(self.gip, "review_ok")
        self.assertEqual(self.status(), "Принята")
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)

    def test_assignee_cannot_accept_own_work(self):
        self.act(self.worker, "accept_own", days="5")
        self.act(self.gip, "approve_days")
        self.act(self.worker, "submit")
        response = self.act(self.worker, "review_ok")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.status(), "На проверке")

    def test_old_review_flow_is_gone_from_the_page(self):
        self.client.force_login(self.gip)
        html = self.client.get(self.detail).content.decode()
        self.assertNotIn("review-submit-modal", html)
        self.assertNotIn(reverse("tasks:send_for_approval", args=[self.task.pk]), html)
