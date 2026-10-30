"""Pult ish oqimi: holatlar, hisoblanadigan maydonlar, rollar va harakatlar.

Ilgari bularning hammasi brauzerda bajarilib, Google Sheets'ga yozilardi.
Endi holat o'tishlari faqat shu yerda, rol va joriy holat tekshiruvi bilan
amalga oshadi — brauzer faqat qaysi harakat kerakligini aytadi.
"""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import Max, Q
from django.utils import timezone

from apps.accounts.models import User
from apps.documents.models import AuditLog
from apps.notifications.services import notify_user
from apps.projects.models import Project
from apps.projects.permissions import ensure_project_member, visible_projects_for
from apps.tasks.models import Task, TaskComment
from apps.tasks.permissions import can_manage_task, resolve_reviewer

from .models import CalendarDay, Flow, ProgressReport, PultSettings, TaskWorkflow
from .models import WorkflowStatus as WS

ACTIVE = (WS.IN_PROGRESS, WS.QUESTION, WS.REVISION)
CLOSED = (WS.ACCEPTED, WS.CANCELLED)

# Pult holati -> platformadagi Task.status. "Отменена" platformada yo'q:
# bunday vazifaning Task.status'i o'zgartirilmaydi.
PLATFORM_STATUS = {
    WS.DRAFT: Task.Status.NEW,
    WS.NEW: Task.Status.NEW,
    WS.DAYS_PROPOSED: Task.Status.NEW,
    WS.IN_PROGRESS: Task.Status.IN_PROGRESS,
    WS.QUESTION: Task.Status.IN_PROGRESS,
    WS.APPROVAL: Task.Status.IN_PROGRESS,
    WS.REVIEW: Task.Status.REVIEW,
    WS.REVISION: Task.Status.REVISION,
    WS.ACCEPTED: Task.Status.COMPLETED,
}
# Vazifa eski kanbanda surilgan bo'lsa, Pult holati shundan olinadi.
FROM_PLATFORM = {
    Task.Status.NEW: WS.NEW,
    Task.Status.IN_PROGRESS: WS.IN_PROGRESS,
    Task.Status.REVIEW: WS.REVIEW,
    Task.Status.REVISION: WS.REVISION,
    Task.Status.APPROVED: WS.ACCEPTED,
    Task.Status.COMPLETED: WS.ACCEPTED,
}
PRIORITY_TO_PULT = {Task.Priority.CRITICAL: 1, Task.Priority.HIGH: 1, Task.Priority.MEDIUM: 2, Task.Priority.LOW: 3}
PRIORITY_FROM_PULT = {1: Task.Priority.HIGH, 2: Task.Priority.MEDIUM, 3: Task.Priority.LOW}

BOSS, GIP, ACCOUNTANT, HR, ADMIN_DEPT, SPECIALIST = (
    "Руководитель", "ГИП", "Бухгалтер", "Кадры", "Админ", "Специалист",
)
NONSTD_CREATORS = (BOSS, GIP, ACCOUNTANT, HR, ADMIN_DEPT)
_DEPT_ROLES = {"кадры": HR, "kadrlar": HR, "hr": HR, "админ": ADMIN_DEPT, "admin": ADMIN_DEPT}


class PultError(Exception):
    """Foydalanuvchiga ko'rsatiladigan xato (HTTP 400/403/409)."""

    def __init__(self, message, status=400):
        super().__init__(message)
        self.message = message
        self.status = status


def today():
    return timezone.localdate()


# ---------------------------------------------------------------- roles

def pult_role(user):
    """Platforma rolini Pult roliga aylantiradi. Mijoz Pultni ko'rmaydi (None)."""
    if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.MANAGER):
        return BOSS
    if user.role in (User.Role.GIP, User.Role.GIP_ASSISTANT):
        return GIP
    if user.role == User.Role.FINANCE:
        return ACCOUNTANT
    if user.role == User.Role.CLIENT:
        return None
    return _DEPT_ROLES.get((user.department or "").strip().lower(), SPECIALIST)


def is_boss(user):
    return pult_role(user) == BOSS


def can_approve(user, task, wf, visible_project_ids=None):
    """Kim ТЗ beradi, muddatni tasdiqlaydi, ishni qabul qiladi.
    ``visible_project_ids`` — ko'p vazifa uchun bir marta hisoblangan to'plam."""
    if is_boss(user):
        return True
    reviewer = resolve_reviewer(task)
    if reviewer is not None and reviewer.id == user.id:
        return True
    if wf.flow == Flow.OTHER:
        return task.creator_id == user.id
    if pult_role(user) != GIP:
        return False
    if visible_project_ids is not None:
        return task.project_id in visible_project_ids
    return visible_projects_for(user).filter(pk=task.project_id).exists()


def acts_as_assignee(user, task):
    # Rahbar xodim telefonda aytgan narsani uning nomidan yozib qo'ya oladi.
    return task.assignee_id == user.id or is_boss(user)


# ---------------------------------------------------------------- workflow rows

def next_number():
    return (TaskWorkflow.objects.aggregate(m=Max("number"))["m"] or 0) + 1


def ensure_workflow(task):
    """Har bir platforma vazifasiga Pult yozuvi (raqam bilan)."""
    try:
        return task.workflow
    except TaskWorkflow.DoesNotExist:
        pass
    for _attempt in range(5):
        try:
            with transaction.atomic():
                return TaskWorkflow.objects.create(
                    task=task, number=next_number(),
                    status=FROM_PLATFORM.get(task.status, WS.NEW),
                    flow=Flow.PROJECT if task.section_id else Flow.OTHER,
                )
        except IntegrityError:
            existing = TaskWorkflow.objects.filter(task=task).first()
            if existing:
                return existing
    raise PultError("Vazifaga raqam berib bo'lmadi, qayta urinib ko'ring.", 409)


def effective_status(task, wf):
    if wf.status == WS.CANCELLED:
        return wf.status
    if PLATFORM_STATUS.get(wf.status) == task.status:
        return wf.status
    return FROM_PLATFORM.get(task.status, wf.status)


def plan_date(task, wf):
    if wf.start_date and wf.days:
        return wf.start_date + timedelta(days=wf.days)
    return task.deadline


def save_workflow(task, wf):
    """Pult yozuvini saqlaydi va platformadagi Task'ni unga moslaydi."""
    wf.save()
    fields = []
    target = PLATFORM_STATUS.get(wf.status)
    if target and task.status != target:
        task.status = target
        fields.append("status")
    if wf.start_date and wf.days:
        plan = plan_date(task, wf)
        if task.deadline != plan:
            task.deadline = plan
            fields.append("deadline")
    if fields:
        task.save(update_fields=fields + ["updated_at"])


# ---------------------------------------------------------------- calendar

class WorkCalendar:
    def __init__(self, settings=None):
        settings = settings or PultSettings.load()
        self.week = settings.work_week_days
        self.days = {d.date: d.is_workday for d in CalendarDay.objects.all()}

    def is_work(self, day):
        if day in self.days:
            return self.days[day]
        wd = day.weekday()  # 0 = dushanba
        return wd != 6 if self.week == 6 else wd < 5

    def sheet_rows(self):
        # Pult interfeysi kalendarni «Календарь» varag'i ko'rinishida o'qiydi
        # (makeCal): A — sana, C — «рабочий»/«выходной», E/F — ish haftasi.
        rows = [["Дата", "", "Тип", "", "Параметр", "Значение"],
                ["", "", "", "", "Рабочих дней в неделе", self.week]]
        rows += [[d.isoformat(), "", "рабочий" if w else "выходной", "", "", ""] for d, w in sorted(self.days.items())]
        return rows


def missed_reports(task, wf, reports, cal, until=None):
    """Ish kunlarida, vazifa faol holatda bo'lgan, lekin hisobot yo'q kunlar soni."""
    if not wf.start_date:
        return 0
    end = until or wf.finished_at or today()
    reported = {r.date for r in reports if not r.status}
    events = sorted(((r.date, r.status) for r in reports if r.status), key=lambda x: x[0])
    miss = 0
    day = wf.start_date + timedelta(days=1)
    while day < end:
        if cal.is_work(day):
            status = WS.IN_PROGRESS
            for d, s in events:
                if d <= day:
                    status = s
                else:
                    break
            if status in ACTIVE and day not in reported:
                miss += 1
        day += timedelta(days=1)
    return miss


# ---------------------------------------------------------------- computed fields

def task_metrics(task, wf, status, settings):
    plan = plan_date(task, wf)
    start = wf.start_date
    out = {"plan": plan, "elapsed": None, "control": "", "delay": None, "points": None}
    if start and plan and status not in (WS.DRAFT, WS.NEW, WS.DAYS_PROPOSED):
        until = wf.finished_at or today()
        total = max(1, (plan - start).days)
        out["elapsed"] = max(0.0, (until - start).days / total)
    if status in ACTIVE and out["elapsed"] is not None:
        if out["elapsed"] >= 0.7 and wf.done < 0.7:
            out["control"] = "ТРЕВОГА 70%"
        elif wf.done + 1e-9 < out["elapsed"]:
            out["control"] = "Отстаёт"
        else:
            out["control"] = "В графике"
    if wf.finished_at and plan:
        out["delay"] = (wf.finished_at - plan).days
    if status == WS.ACCEPTED and out["delay"] is not None:
        out["points"] = kpi_points(out["delay"], wf.reworks, wf.missed_reports, settings)
    return out


def kpi_points(delay, reworks, missed, s):
    if delay < 0:
        timing = s.points_early
    elif delay == 0:
        timing = s.points_ontime
    elif delay <= s.late_days:
        timing = s.points_late_small
    else:
        timing = s.points_late_big
    quality = s.points_clean if not reworks else max(s.quality_min, -s.points_per_rework * reworks)
    penalty = min(s.missed_max, s.points_per_missed * missed)
    return timing + quality - penalty


def kpi_config(s):
    return {
        "early": s.points_early, "ontime": s.points_ontime, "lateSmall": s.points_late_small,
        "lateDays": s.late_days, "lateBig": s.points_late_big, "clean": s.points_clean,
        "perRework": s.points_per_rework, "qualityMin": s.quality_min,
        "perMissed": s.points_per_missed, "missedMax": s.missed_max, "minTasks": s.min_tasks,
        "levels": [
            {"cat": "A", "min": s.level_a, "bonus": s.bonus_a},
            {"cat": "B", "min": s.level_b, "bonus": s.bonus_b},
            {"cat": "C", "min": s.level_c, "bonus": s.bonus_c},
            {"cat": "D", "min": -100, "bonus": s.bonus_d},
        ],
    }


def _iso(d):
    return d.isoformat() if d else None


def task_payload(task, wf, settings):
    status = effective_status(task, wf)
    m = task_metrics(task, wf, status, settings)
    return {
        "id": wf.number, "uuid": str(task.pk), "created": _iso(timezone.localtime(task.created_at).date()),
        "assignee": task.assignee.full_name if task.assignee_id else None,
        "project": task.project.name, "task": task.title, "type": wf.type or None,
        "priority": PRIORITY_TO_PULT.get(task.priority, 2), "days": wf.days,
        "amount": wf.amount, "hours": wf.hours, "start": _iso(wf.start_date), "plan": _iso(m["plan"]),
        "status": status, "done": wf.done, "elapsed": m["elapsed"], "control": m["control"] or None,
        "source_ok": "Да" if wf.source_ok else "Нет", "finished": _iso(wf.finished_at),
        "reworks": wf.reworks, "missed": wf.missed_reports, "delay": m["delay"], "points": m["points"],
        "comment": task.description or None, "section": wf.section, "flow": wf.flow, "stage": wf.stage or None,
        "apprSince": _iso(wf.approval_since), "approver": wf.approver_kind or None,
        "dept": wf.dept or None, "tz": wf.tz or None, "url": f"/tasks/{task.pk}/",
    }


# ---------------------------------------------------------------- visibility

def visible_tasks(user):
    qs = Task.objects.all() if is_boss(user) else Task.objects.filter(
        Q(project__in=visible_projects_for(user)) | Q(assignee=user)
    )
    return qs.select_related(
        "project", "assignee", "creator", "reviewer", "workflow",
        "section__gip", "section__sub_object__gip",
    ).distinct()


def get_task(user, number):
    wf = TaskWorkflow.objects.filter(number=number).select_related("task").first()
    if wf is None or not visible_tasks(user).filter(pk=wf.task_id).exists():
        raise PultError(f"Задача №{number} не найдена. Обновите страницу.", 404)
    return wf.task, wf


# ---------------------------------------------------------------- logging helpers

def _actor_name(user):
    return user.full_name or user.email


def log_status(task, wf, user, text):
    ProgressReport.objects.create(
        task=task, author=user, date=today(), done=wf.done,
        comment=f"▶ {text} · {_actor_name(user)}", status=wf.status,
    )


def _notify(user, target, title, message, task):
    if target is not None and target.id != user.id:
        notify_user(target, "task", title, message, link=f"/tasks/{task.pk}/")


def _approver_for(task):
    return resolve_reviewer(task) or task.creator


# ---------------------------------------------------------------- actions

def _days(params, key="days", required=True):
    raw = params.get(key)
    if raw in (None, ""):
        if required:
            raise PultError("Укажите срок в днях.")
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise PultError("Срок должен быть целым числом дней.")
    if value < 1:
        raise PultError("Срок — от 1 дня.")
    return value


def _text(params, key, required=True):
    value = str(params.get(key) or "").strip()
    if required and not value:
        raise PultError("Заполните текст.")
    return value


# Har bir harakat: (kim bajaradi, qaysi holatlardan, funksiya).
# Funksiya wf ni o'zgartiradi va (jurnal matni, izoh matni, kimga xabar) qaytaradi.

def _a_accept(task, wf, p):
    if not wf.days:
        raise PultError("Срок не назван: используйте «Принять и назвать срок».")
    wf.status, wf.start_date = WS.IN_PROGRESS, today()
    return f"В работе: принял, срок {wf.days} дн.", "", "approver"


def _a_accept_own(task, wf, p):
    days, note = _days(p), _text(p, "note", False)
    wf.status, wf.days = WS.DAYS_PROPOSED, days
    return f"На согласовании: предложил срок {days} дн." + (f" — {note}" if note else ""), note, "approver"


def _a_submit(task, wf, p):
    note = _text(p, "note", False)
    wf.status, wf.done, wf.finished_at, wf.source_ok = WS.REVIEW, 1, today(), bool(p.get("src"))
    return "На проверке: сдал работу" + (f" — {note}" if note else ""), note, "approver"


def _a_to_appr(task, wf, p):
    what = _text(p, "what")
    wf.status, wf.approval_since, wf.approver_kind = WS.APPROVAL, today(), "ГИП"
    return f"Согласование: {what}", what, "approver"


def _a_question(task, wf, p):
    q = _text(p, "q")
    wf.status = WS.QUESTION
    return f"Есть вопрос: {q}", q, "approver"


def _a_issue_tz(task, wf, p):
    wf.status, wf.tz, wf.days = WS.NEW, _text(p, "tz", False), _days(p, required=False)
    return "Новая: ТЗ выдано", "", "assignee"


def _a_approve_days(task, wf, p):
    wf.status, wf.start_date = WS.IN_PROGRESS, today()
    return f"В работе: срок {wf.days} дн. утверждён", "", "assignee"


def _a_change_days(task, wf, p):
    old = wf.days
    wf.status, wf.start_date, wf.days = WS.IN_PROGRESS, today(), _days(p)
    return f"В работе: утверждён срок {wf.days} дн. (предлагал {old if old else '—'})", "", "assignee"


def _a_reject_days(task, wf, p):
    why = _text(p, "why")
    wf.status = WS.NEW
    return f"Новая: срок не утверждён — {why}", why, "assignee"


def _end_approval(wf):
    pause = (today() - wf.approval_since).days if wf.approval_since else 0
    if wf.days and pause > 0 and wf.start_date:
        wf.days += pause  # pauza ijrochining muddatini yemaydi
    wf.status, wf.approval_since, wf.approver_kind = WS.IN_PROGRESS, None, ""
    return f", срок +{pause} дн. за паузу" if pause and wf.start_date else ""


def _a_appr_ok(task, wf, p):
    return "В работе: согласовано" + _end_approval(wf), "", "assignee"


def _a_appr_remarks(task, wf, p):
    why = _text(p, "why")
    return f"В работе: замечания по согласованию — {why}" + _end_approval(wf), why, "assignee"


def _a_appr_client(task, wf, p):
    wf.approver_kind = "Заказчик"
    return "Согласование: передано заказчику, ведёт ГИП", "", "assignee"


def _a_answer(task, wf, p):
    a = _text(p, "a")
    wf.status = WS.IN_PROGRESS
    return f"В работе: ответ ГИПа — {a}", a, "assignee"


def _a_review_ok(task, wf, p):
    reports = list(ProgressReport.objects.filter(task=task))
    wf.missed_reports = missed_reports(task, wf, reports, WorkCalendar())
    wf.status, wf.done = WS.ACCEPTED, 1
    wf.finished_at = wf.finished_at or today()
    return "Принята" + (f", пропущено отчётов: {wf.missed_reports}" if wf.missed_reports else ""), "", "assignee"


def _a_review_back(task, wf, p):
    why = _text(p, "why")
    wf.status, wf.reworks, wf.finished_at = WS.REVISION, wf.reworks + 1, None
    wf.done = min(wf.done, 0.9)
    return f"На доработке: {why}", why, "assignee"


KANBAN_COLUMNS = {
    "new": ((WS.DRAFT, WS.NEW, WS.DAYS_PROPOSED), WS.NEW),
    "work": ((WS.IN_PROGRESS, WS.QUESTION, WS.REVISION, WS.APPROVAL), WS.IN_PROGRESS),
    "review": ((WS.REVIEW,), WS.REVIEW),
    "done": ((WS.ACCEPTED,), WS.ACCEPTED),
}


def _a_move(task, wf, p):
    """Kanbanda kartochkani surish (faqat rahbar)."""
    col = p.get("col")
    if col not in KANBAN_COLUMNS:
        raise PultError("Неизвестная колонка.")
    statuses, target = KANBAN_COLUMNS[col]
    current = wf.status
    if current in statuses:
        return None, "", None
    note = ""
    if col == "work" and current == WS.REVIEW:
        target = WS.REVISION
        wf.reworks += 1
        note = f" · доработка №{wf.reworks}"
    if col == "work" and current == WS.ACCEPTED:
        note = " · приёмка отменена"
    if col == "done":
        wf.done, wf.finished_at = 1, today()
    else:
        wf.finished_at = None
    if col != "new" and wf.days and not wf.start_date:
        wf.start_date = today()
    wf.status = target
    return f"{target}: перенесено на канбане{note}", "", "assignee"


ASSIGNEE, APPROVER = "assignee", "approver"
ACTIONS = {
    "accept": (ASSIGNEE, (WS.NEW,), _a_accept),
    "accept_own": (ASSIGNEE, (WS.NEW,), _a_accept_own),
    "submit": (ASSIGNEE, (WS.IN_PROGRESS, WS.REVISION), _a_submit),
    "to_appr": (ASSIGNEE, (WS.IN_PROGRESS, WS.REVISION), _a_to_appr),
    "question": (ASSIGNEE, (WS.IN_PROGRESS, WS.REVISION), _a_question),
    "issue_tz": (APPROVER, (WS.DRAFT,), _a_issue_tz),
    "approve_days": (APPROVER, (WS.DAYS_PROPOSED,), _a_approve_days),
    "change_days": (APPROVER, (WS.DAYS_PROPOSED,), _a_change_days),
    "reject_days": (APPROVER, (WS.DAYS_PROPOSED,), _a_reject_days),
    "appr_ok": (APPROVER, (WS.APPROVAL,), _a_appr_ok),
    "appr_remarks": (APPROVER, (WS.APPROVAL,), _a_appr_remarks),
    "appr_client": (APPROVER, (WS.APPROVAL,), _a_appr_client),
    "answer": (APPROVER, (WS.QUESTION,), _a_answer),
    "review_ok": (APPROVER, (WS.REVIEW,), _a_review_ok),
    "review_back": (APPROVER, (WS.REVIEW,), _a_review_back),
    "move": (BOSS, None, _a_move),
}


@transaction.atomic
def run_action(user, number, action, params):
    if action not in ACTIONS:
        raise PultError("Неизвестное действие.")
    task, wf = get_task(user, number)
    wf = TaskWorkflow.objects.select_for_update().get(pk=wf.pk)
    who, allowed, handler = ACTIONS[action]
    wf.status = effective_status(task, wf)

    expected = params.get("expect_status")
    if expected and expected != wf.status:
        raise PultError(f"Задача №{wf.number} уже изменилась: сейчас «{wf.status}». Посмотрите ещё раз.", 409)
    if allowed is not None and wf.status not in allowed:
        raise PultError(f"Это действие недоступно в статусе «{wf.status}».", 409)
    if who == ASSIGNEE and not acts_as_assignee(user, task):
        raise PultError("Это может сделать только исполнитель.", 403)
    if who == APPROVER and not can_approve(user, task, wf):
        raise PultError("Это решение принимает ГИП или руководитель.", 403)
    if who == BOSS and not is_boss(user):
        raise PultError("Перетаскивать карточки может только руководитель.", 403)

    log, comment, notify = handler(task, wf, params)
    if log is None:
        return task, wf
    save_workflow(task, wf)
    log_status(task, wf, user, log)
    if action == "submit":
        ProgressReport.objects.create(task=task, author=user, date=today(), done=1, comment="Отчёт: сдано на проверку")
    if comment:
        TaskComment.objects.create(task=task, user=user, content=log)
    AuditLog.log(obj=task, action="status_changed", user=user, details={"pult": action, "status": wf.status})
    title = f"№{wf.number}: {wf.status}"
    if notify == "assignee":
        _notify(user, task.assignee, title, f"«{task.title}»: {log}", task)
    elif notify == "approver":
        _notify(user, _approver_for(task), title, f"{_actor_name(user)} · «{task.title}»: {log}", task)
    return task, wf


# ---------------------------------------------------------------- daily report

@transaction.atomic
def send_report(user, items, note):
    if not items:
        raise PultError("Нет задач для отчёта.")
    rows = []
    for item in items:
        task, wf = get_task(user, item.get("id"))
        if not acts_as_assignee(user, task):
            raise PultError(f"№{wf.number}: отчёт сдаёт исполнитель.", 403)
        if effective_status(task, wf) not in ACTIVE:
            raise PultError(f"№{wf.number}: задача не в работе, отчёт не нужен.", 409)
        try:
            pct = max(0, min(100, int(item.get("done"))))
        except (TypeError, ValueError):
            raise PultError("Процент — число от 0 до 100.")
        if round(wf.done * 100) != pct:
            wf.done = pct / 100
            wf.save(update_fields=["done", "updated_at"])
        rows.append(ProgressReport(task=task, author=user, date=today(), done=pct / 100,
                                   comment=f"Отчёт: {note}" if note else "Отчёт"))
    ProgressReport.objects.bulk_create(rows)
    return len(rows)


# ---------------------------------------------------------------- create / edit

def resolve_person(name):
    name = str(name or "").strip()
    if not name:
        raise PultError("Выберите исполнителя.")
    users = list(User.objects.filter(is_active=True, full_name=name)[:2])
    if not users:
        raise PultError(f"Сотрудник «{name}» не найден.")
    if len(users) > 1:
        raise PultError(f"Найдено несколько сотрудников «{name}». Переименуйте одного из них в «Пользователи».")
    return users[0]


def resolve_project(user, name, nonstd=False):
    name = str(name or "").strip()
    if nonstd and name in ("", "GASTEC"):
        return internal_project(user)
    if not name:
        raise PultError("Выберите проект.")
    projects = list(visible_projects_for(user).filter(name=name)[:2])
    if not projects:
        raise PultError(f"Проект «{name}» не найден или недоступен.")
    if len(projects) > 1:
        raise PultError(f"Несколько проектов называются «{name}».")
    return projects[0]


def internal_project(user):
    """Loyihaga tegishli bo'lmagan ichki ishlar (kadrlar, xo'jalik...) shu loyihaga yoziladi."""
    s = PultSettings.load()
    if s.internal_project_id is None:
        s.internal_project = Project.objects.create(
            # Pultda kompaniyaning o'z «loyihasi» shu nom bilan yuritilgan (moliya, ichki vazifalar).
            name="GASTEC", created_by=user, description="Внутренние задачи и деньги компании (создан Пультом).",
        )
        s.save(update_fields=["internal_project"])
    return s.internal_project


def _num(value, cast=float):
    if value in (None, ""):
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        raise PultError("Неверное число.")


def _section(project, value):
    """Состав qatori ID si shu loyihaniki ekanini tekshiradi."""
    if value in (None, ""):
        return None
    from .models import PlanRow
    section = _num(value, int)
    if not PlanRow.objects.filter(pk=section, project=project).exists():
        raise PultError("Раздел не найден в составе этого проекта.")
    return section


def _date(value):
    if not value:
        return None
    from datetime import date
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise PultError("Неверная дата.")


@transaction.atomic
def create_task(user, data):
    role = pult_role(user)
    nonstd = data.get("flow") == Flow.OTHER and not data.get("section")
    if role not in (BOSS, GIP) and not (nonstd and role in NONSTD_CREATORS):
        raise PultError("Ставить задачи может ГИП или руководитель.", 403)
    title = str(data.get("task") or "").strip()
    if not title:
        raise PultError("Напишите, что нужно сделать.")
    assignee = resolve_person(data.get("assignee"))
    project = resolve_project(user, data.get("project"), nonstd=nonstd)
    days = _days(data, required=False)
    status = data.get("status") or (WS.IN_PROGRESS if days else WS.NEW)
    if status not in (WS.DRAFT, WS.NEW, WS.IN_PROGRESS):
        status = WS.NEW
    task = Task.objects.create(
        title=title, description=str(data.get("comment") or "").strip() or None, project=project,
        assignee=assignee, creator=user, priority=PRIORITY_FROM_PULT.get(_num(data.get("priority"), int), Task.Priority.MEDIUM),
    )
    wf = ensure_workflow(task)
    wf.status, wf.days, wf.type = status, days, str(data.get("type") or "")
    wf.hours, wf.amount = _num(data.get("hours")), _num(data.get("amount"))
    wf.start_date = (_date(data.get("start")) or today()) if status == WS.IN_PROGRESS else None
    wf.section = _section(project, data.get("section"))
    wf.flow = Flow.PROJECT if data.get("flow") == Flow.PROJECT or wf.section else Flow.OTHER
    wf.stage, wf.dept, wf.tz = str(data.get("stage") or ""), str(data.get("dept") or ""), str(data.get("tz") or "")
    if wf.section and not wf.stage:
        wf.stage = "Проектирование"
    save_workflow(task, wf)
    log_status(task, wf, user, f"{wf.status}: поставлена")
    AuditLog.log(obj=task, action="created", user=user, details={"pult": True})
    ensure_project_member(project, assignee)
    _notify(user, assignee, "Новая задача", f"№{wf.number} «{task.title}»", task)
    return task, wf


EDITABLE_STATUSES = {s for s, _l in WS.choices}


@transaction.atomic
def edit_task(user, number, data):
    """To'liq tahrirlash (rahbar yoki vazifani boshqara oladigan kishi)."""
    task, wf = get_task(user, number)
    if not (is_boss(user) or can_manage_task(user, task)):
        raise PultError("Нет прав на изменение этой задачи.", 403)
    wf = TaskWorkflow.objects.select_for_update().get(pk=wf.pk)
    old_status, old_assignee, old_done = effective_status(task, wf), task.assignee_id, wf.done

    title = str(data.get("task") or "").strip()
    if not title:
        raise PultError("Напишите, что нужно сделать.")
    task.title = title
    task.description = str(data.get("comment") or "").strip() or None
    task.assignee = resolve_person(data.get("assignee"))
    if data.get("project") != task.project.name:
        task.project = resolve_project(user, data.get("project"))
    task.priority = PRIORITY_FROM_PULT.get(_num(data.get("priority"), int), task.priority)
    task.save()

    status = data.get("status") or old_status
    if status not in EDITABLE_STATUSES:
        raise PultError("Неизвестный статус.")
    wf.status = status
    wf.type = str(data.get("type") or "")
    wf.days = _days(data, required=False)
    wf.start_date = _date(data.get("start"))
    if wf.days and not wf.start_date and status not in (WS.DRAFT, WS.NEW, WS.DAYS_PROPOSED):
        wf.start_date = today()
    wf.hours, wf.amount = _num(data.get("hours")), _num(data.get("amount"))
    if "section" in data:
        wf.section = _section(task.project, data.get("section"))
        if wf.section:
            wf.flow = Flow.PROJECT
    if "done" in data:
        wf.done = max(0.0, min(1.0, _num(data.get("done")) or 0.0))
    if "source_ok" in data:
        wf.source_ok = data.get("source_ok") in (True, "Да")
    if "finished" in data:
        wf.finished_at = _date(data.get("finished"))
    if status == WS.ACCEPTED and not wf.finished_at:
        wf.finished_at = today()
    if "reworks" in data:
        wf.reworks = max(0, _num(data.get("reworks"), int) or 0)
    if "missed" in data:
        wf.missed_reports = max(0, _num(data.get("missed"), int) or 0)
    save_workflow(task, wf)

    if status != old_status:
        log_status(task, wf, user, f"{status}: изменено вручную")
    if round(wf.done * 100) != round(old_done * 100):
        ProgressReport.objects.create(task=task, author=user, date=today(), done=wf.done, comment="Записано на сайте")
    AuditLog.log(obj=task, action="updated", user=user, details={"pult": True})
    if task.assignee_id != old_assignee:
        ensure_project_member(task.project, task.assignee)
        _notify(user, task.assignee, "Задача назначена вам", f"№{wf.number} «{task.title}»", task)
    return task, wf
