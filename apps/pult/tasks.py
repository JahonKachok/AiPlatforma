"""Pult eslatmalari (Celery Beat): kunlik hisobot va qaror kutayotganlar.

Ikkala vazifa ham kun davomida qayta ishga tushsa, bir kishiga bir kunda bitta
xabar yuboradi (sarlavha + sana bo'yicha tekshiriladi).
"""
from collections import defaultdict
from datetime import timedelta

from celery import shared_task
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.notifications.services import notify_user
from apps.projects.permissions import visible_projects_for
from apps.tasks.permissions import resolve_reviewer

from .models import ProgressReport, TaskWorkflow
from .models import WorkflowStatus as WS
from .services import ACTIVE, BOSS, GIP, WorkCalendar, can_approve, effective_status, pult_role, today

REPORT_TITLE = "Пульт: отметьте процент за сегодня"
DIGEST_TITLE = "Пульт: ждут вашего решения"
PENDING = (WS.DRAFT, WS.DAYS_PROPOSED, WS.APPROVAL, WS.REVIEW, WS.QUESTION)
PENDING_TEXT = {
    WS.DRAFT: "ждут ТЗ", WS.DAYS_PROPOSED: "согласовать срок", WS.APPROVAL: "на согласовании",
    WS.REVIEW: "проверить работу", WS.QUESTION: "вопросы",
}


def _sent_today(user, title):
    # Sana emas, oxirgi 20 soat: kun chegarasidagi vaqt mintaqasi farqlari ikkinchi xabarga olib kelmaydi.
    since = timezone.now() - timedelta(hours=20)
    return Notification.objects.filter(user=user, title=title, created_at__gte=since).exists()


def _plural(n, one, few, many):
    n100, n10 = abs(n) % 100, abs(n) % 10
    if 10 < n100 < 20:
        return many
    return one if n10 == 1 else few if 1 < n10 < 5 else many


@shared_task
def remind_daily_reports():
    """Ish kuni oxirida: faol vazifasi bor, lekin bugun foiz belgilamagan ijrochilarga."""
    day = today()
    if not WorkCalendar().is_work(day):
        return 0
    active = (TaskWorkflow.objects.filter(status__in=ACTIVE, start_date__lt=day, task__assignee__isnull=False)
              .select_related("task", "task__assignee"))
    reported = set(ProgressReport.objects.filter(date=day, status="").values_list("task_id", flat=True))
    missing = defaultdict(list)
    for wf in active:
        if effective_status(wf.task, wf) in ACTIVE and wf.task_id not in reported:
            missing[wf.task.assignee].append(wf)
    sent = 0
    for user, wfs in missing.items():
        if not user.is_active or _sent_today(user, REPORT_TITLE):
            continue
        names = "; ".join(f"№{wf.number} {wf.task.title}" for wf in wfs[:5]) + ("…" if len(wfs) > 5 else "")
        notify_user(user, "task", REPORT_TITLE,
                    f"{len(wfs)} {_plural(len(wfs), 'задача', 'задачи', 'задач')} без отчёта: {names}. "
                    "Откройте «Моя работа» и нажмите «Отправить отчёт».", link="/pult/")
        sent += 1
    return sent


def _candidates(pending_tasks):
    """Qaror qabul qila oladigan barcha odamlar: rahbarlar, ГИПлар, tekshiruvchilar va mualliflar."""
    ids = set()
    for wf in pending_tasks:
        ids.add(wf.task.creator_id)
        reviewer = resolve_reviewer(wf.task)
        if reviewer is not None:
            ids.add(reviewer.pk)
    q = Q(pk__in=ids) | Q(is_superuser=True) | Q(role__in=(User.Role.ADMIN, User.Role.MANAGER, User.Role.GIP, User.Role.GIP_ASSISTANT))
    return User.objects.filter(q, is_active=True).distinct()


@shared_task
def digest_pending_decisions():
    """Ertalab: har bir ГИП/rahbarga uning qarorini kutayotgan vazifalar soni."""
    if not WorkCalendar().is_work(today()):
        return 0
    pending = [
        wf for wf in TaskWorkflow.objects.filter(status__in=PENDING).select_related(
            "task", "task__project", "task__creator", "task__reviewer", "task__section__gip", "task__section__sub_object__gip")
        if effective_status(wf.task, wf) in PENDING
    ]
    if not pending:
        return 0
    sent = 0
    for user in _candidates(pending):
        role = pult_role(user)
        if role is None or _sent_today(user, DIGEST_TITLE):
            continue
        visible = None if role == BOSS else set(visible_projects_for(user).values_list("pk", flat=True))
        counts = defaultdict(int)
        for wf in pending:
            if can_approve(user, wf.task, wf, visible if role == GIP else None):
                counts[effective_status(wf.task, wf)] += 1
        if not counts:
            continue
        total = sum(counts.values())
        parts = ", ".join(f"{PENDING_TEXT[s]}: {n}" for s, n in counts.items())
        notify_user(user, "approval", DIGEST_TITLE,
                    f"{total} {_plural(total, 'задача ждёт', 'задачи ждут', 'задач ждут')} вашего решения — {parts}.",
                    link="/pult/")
        sent += 1
    return sent
