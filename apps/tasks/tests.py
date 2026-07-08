from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.projects.models import Project, ProjectMember

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
