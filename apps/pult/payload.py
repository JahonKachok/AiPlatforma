"""Pult interfeysi bir so'rovda oladigan ma'lumot: avval Google Sheets'ning
bir nechta varag'idan o'qilardi, endi platforma bazasidan yig'iladi."""
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.projects.models import Project, ProjectMember
from apps.projects.permissions import visible_projects_for

from .finance import can_finance, finance_payload
from .models import ProgressReport, PultSettings, TaskTemplate, TaskWorkflow
from .plan import ciphers_json, disciplines_json, plan_state, stages_json
from .services import (
    BOSS, GIP, WorkCalendar, can_approve, ensure_workflow, is_boss, kpi_config, pult_role, task_payload,
    today, visible_tasks,
)

REPORT_HISTORY_DAYS = 180
CLOSED_PROJECT = (Project.Status.COMPLETED, Project.Status.CANCELLED)


def _member_project_names(user):
    now = timezone.now()
    return sorted(set(
        ProjectMember.objects.filter(user=user)
        .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
        .values_list("project__name", flat=True)
    ))


def _viewer(user):
    role = pult_role(user)
    if role is None:
        return {"role": None, "unknown": True, "email": user.email, "name": user.full_name}
    return {
        "role": role, "person": user.full_name, "email": user.email, "owner": role == BOSS, "pages": None,
        "projects": _member_project_names(user) if role == GIP else [],
    }


def _people():
    out = []
    users = User.objects.filter(is_active=True).exclude(role=User.Role.CLIENT).select_related("pult_settings")
    for u in users.prefetch_related("disciplines"):
        codes = ", ".join(d.code for d in u.disciplines.all())
        ps = getattr(u, "pult_settings", None)
        out.append({
            "id": str(u.pk), "first": u.full_name, "last": "", "name": u.full_name,
            "role": u.get_role_display(), "sections": u.department or codes or "",
            # Sozlanmagan xodim — shtatda (oklad): bo'limlari shartnoma yaratmaydi.
            "pay": ps.pay_type if ps else "Оклад", "norm": ps.norm_hours if ps else 40,
            "stageRole": ps.stage_role if ps else "", "inTasks": "Да",
        })
    return out


def _access(user):
    if not is_boss(user):
        return []
    rows = []
    for u in User.objects.filter(is_active=True).exclude(role=User.Role.CLIENT):
        role = pult_role(u)
        rows.append({"person": u.full_name, "email": u.email, "role": role,
                     "projects": _member_project_names(u) if role == GIP else [], "pages": []})
    return rows


def build_payload(user):
    settings = PultSettings.load()
    tasks = list(visible_tasks(user))
    workflows = {}
    for task in tasks:
        try:
            workflows[task.pk] = task.workflow
        except TaskWorkflow.DoesNotExist:
            workflows[task.pk] = ensure_workflow(task)

    by_id = {t.pk: t for t in tasks}
    since = today() - timedelta(days=REPORT_HISTORY_DAYS)
    progress = [
        {"date": r.date.isoformat(), "task_id": workflows[r.task_id].number,
         "assignee": by_id[r.task_id].assignee.full_name if by_id[r.task_id].assignee_id else "",
         "done": r.done, "comment": r.comment}
        for r in ProgressReport.objects.filter(task_id__in=by_id.keys(), date__gte=since)
    ]
    projects = Project.objects.all() if is_boss(user) else visible_projects_for(user)
    visible_ids = set(projects.values_list("pk", flat=True))
    task_rows = []
    for t in tasks:
        row = task_payload(t, workflows[t.pk], settings)
        row["canApprove"] = can_approve(user, t, workflows[t.pk], visible_ids)
        task_rows.append(row)
    plan = plan_state(user)
    finance = finance_payload(user)
    return {
        "viewer": _viewer(user),
        "access": _access(user),
        "tasks": task_rows,
        "plan": plan["rows"], "planVersion": plan["version"],
        "disc": disciplines_json(), "stages": stages_json(), "ciphers": ciphers_json(user),
        **finance,
        "progress": progress,
        "people": _people(),
        "projects": [
            {"name": p.name, "status": "Закрыт" if p.status in CLOSED_PROJECT else "Открыт",
             "client": p.client_name or "", "full": p.description or p.name}
            for p in projects.order_by("name")
        ],
        "templates": [
            {"name": t.name, "desc": t.description, "days": t.days, "hours": t.hours, "dept": t.dept}
            for t in TaskTemplate.objects.all()
        ],
        "kpi": kpi_config(settings),
        "calendar": WorkCalendar(settings).sheet_rows(),
        "features": {"plan": True, "finance": can_finance(user)},
        "generatedAt": timezone.now().isoformat(),
    }
