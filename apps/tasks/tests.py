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
        self.client.get(reverse("tasks:delete_comment", args=[self.task.pk, comment.pk]))
        self.assertFalse(TaskComment.objects.filter(pk=comment.pk).exists())

    def test_non_owner_cannot_delete_comment(self):
        comment = TaskComment.objects.create(task=self.task, user=self.assignee, content="hi")
        self.client.force_login(self.other)
        response = self.client.get(reverse("tasks:delete_comment", args=[self.task.pk, comment.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(TaskComment.objects.filter(pk=comment.pk).exists())

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
        self.client.force_login(self.manager)
        response = self.client.get(reverse("tasks:create"))
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
