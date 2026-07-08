from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.projects.models import Project, ProjectMember
from apps.tasks.models import Task

from .models import Notification
from .tasks import check_deadlines


class DeadlineDedupTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(email="creator@example.com", password="pw12345!", full_name="Creator", role=User.Role.MANAGER)
        self.assignee = User.objects.create_user(email="assignee@example.com", password="pw12345!", full_name="Assignee", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="P1", created_by=self.creator)
        ProjectMember.objects.create(project=self.project, user=self.assignee)
        self.task = Task.objects.create(
            title="Urgent", project=self.project, assignee=self.assignee, creator=self.creator,
            deadline=timezone.now().date() + timedelta(hours=12),
        )

    def test_dedup_prevents_duplicate_deadline_notifications(self):
        check_deadlines()
        first_count = Notification.objects.filter(user=self.assignee, type="deadline").count()
        self.assertEqual(first_count, 1)

        check_deadlines()
        second_count = Notification.objects.filter(user=self.assignee, type="deadline").count()
        self.assertEqual(second_count, 1)


class TaskAssignmentNotificationTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(email="creator2@example.com", password="pw12345!", full_name="Creator", role=User.Role.MANAGER)
        self.assignee = User.objects.create_user(email="assignee2@example.com", password="pw12345!", full_name="Assignee", role=User.Role.DESIGNER)
        self.project = Project.objects.create(name="P2", created_by=self.creator)
        for u in [self.creator, self.assignee]:
            ProjectMember.objects.create(project=self.project, user=u)

    def test_creating_task_with_assignee_notifies_them(self):
        self.client.force_login(self.creator)
        self.client.post(reverse("tasks:create"), {
            "title": "New task", "project": self.project.pk, "assignee": self.assignee.pk,
            "status": "new", "priority": "medium",
        })
        self.assertTrue(Notification.objects.filter(user=self.assignee, type="task").exists())

    def test_assigning_to_self_does_not_notify(self):
        self.client.force_login(self.creator)
        self.client.post(reverse("tasks:create"), {
            "title": "My own task", "project": self.project.pk, "assignee": self.creator.pk,
            "status": "new", "priority": "medium",
        })
        self.assertFalse(Notification.objects.filter(user=self.creator, type="task").exists())
