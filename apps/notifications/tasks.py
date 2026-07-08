import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_notification_email(user_id, title, message, link=None):
    from apps.accounts.models import User

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    if not user.email:
        return
    body = message
    if link:
        body = f"{message}\n\n{settings.FRONTEND_URL}{link}"
    send_mail(title, body, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)


@shared_task
def send_notification_telegram(user_id, title, message):
    from apps.accounts.models import User
    from apps.telegram_bot.services import send_message

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return
    if not user.telegram_chat_id:
        return
    send_message(user.telegram_chat_id, f"<b>{title}</b>\n{message}")


@shared_task
def check_deadlines():
    """Hourly scan for tasks/documents/projects due within 24h or overdue,
    notifying the relevant users. Ports scheduler.py's dedup logic: skip if
    an identical deadline notification was already sent within DEDUP_HOURS."""
    from datetime import timedelta

    from apps.documents.models import Document, DocumentStatus
    from apps.notifications.services import notify_user
    from apps.projects.models import Project
    from apps.tasks.models import Task

    DEDUP_HOURS = 23
    now = timezone.now()
    soon = now + timedelta(hours=24)
    today = now.date()
    soon_date = soon.date()
    dedup_since = now - timedelta(hours=DEDUP_HOURS)

    def already_notified(user, link):
        from apps.notifications.models import Notification
        return Notification.objects.filter(
            user=user, type="deadline", link=link, created_at__gte=dedup_since
        ).exists()

    for task in Task.objects.exclude(status__in=[Task.Status.COMPLETED, Task.Status.APPROVED]).filter(deadline__isnull=False):
        link = f"/tasks/{task.pk}/"
        if task.deadline < today:
            for user in filter(None, [task.assignee, task.creator]):
                if not already_notified(user, link):
                    notify_user(user, "deadline", "Task overdue", f'"{task.title}" is overdue.', link=link)
        elif task.deadline <= soon_date:
            if task.assignee and not already_notified(task.assignee, link):
                notify_user(task.assignee, "deadline", "Task due soon", f'"{task.title}" is due soon.', link=link)

    for document in Document.objects.exclude(
        status__in=[DocumentStatus.APPROVED, DocumentStatus.ARCHIVED]
    ).filter(deadline__isnull=False, deadline__lte=soon_date):
        link = f"/documents/{document.pk}/"
        if not already_notified(document.uploaded_by, link):
            notify_user(document.uploaded_by, "deadline", "Document deadline approaching", f'"{document.name}" is due soon.', link=link)

    for project in Project.objects.filter(
        status=Project.Status.ACTIVE, deadline__isnull=False, deadline__lte=soon_date
    ):
        link = f"/projects/{project.pk}/"
        if not already_notified(project.created_by, link):
            notify_user(project.created_by, "deadline", "Project deadline approaching", f'"{project.name}" is due soon.', link=link)
