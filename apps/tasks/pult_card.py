"""Vazifa sahifasi (/tasks/<id>/) uchun Pult tuzilishi.

Vazifa Pult oqimi bilan yuradi (apps/pult/services.py): holat, muddat kunlarda,
ТЗ, kunlik hisobot, kelishuv, tekshiruv va KPI. Bu modul sahifaga kerakli
hammasini bir joyda yig'adi: holat, «keyingi qadam», mavjud harakatlar (pult.js
dagi actionsFor bilan bir xil qoidalar), muddat ko'rsatkichlari va tarix.
Harakatning o'zi server tomonda — services.run_action.
"""
from django.utils.translation import gettext_lazy as _

from apps.pult.models import PlanRow, ProgressReport, PultSettings
from apps.pult.models import WorkflowStatus as WS
from apps.pult.services import (
    ACTIVE, CLOSED, _approver_for, can_approve, effective_status, ensure_workflow, task_metrics, today,
)

STATUS_LABELS = {
    WS.DRAFT: _("Draft"),
    WS.NEW: _("Brief issued"),
    WS.DAYS_PROPOSED: _("Term proposed"),
    WS.IN_PROGRESS: _("In progress"),
    WS.QUESTION: _("Has a question"),
    WS.APPROVAL: _("On approval"),
    WS.REVIEW: _("On review"),
    WS.REVISION: _("Needs revision"),
    WS.ACCEPTED: _("Accepted"),
    WS.CANCELLED: _("Cancelled"),
}
STATUS_TONE = {
    WS.ACCEPTED: "badge-success", WS.REVIEW: "badge-info", WS.APPROVAL: "badge-info",
    WS.QUESTION: "badge-warning", WS.REVISION: "badge-warning", WS.DAYS_PROPOSED: "badge-warning",
    WS.CANCELLED: "badge-danger", WS.IN_PROGRESS: "badge-purple",
}
NOT_STARTED = (WS.DRAFT, WS.NEW, WS.DAYS_PROPOSED)

# Harakat maydonlari: (nom, tur, yorliq, majburiy)
F_DAYS = ("days", "number", _("Term, days"), True)
F_NOTE = ("note", "textarea", _("Comment (optional)"), False)


def _actions(user, task, wf, status):
    """Foydalanuvchi shu vazifa bilan hozir nima qila oladi (pult.js: actionsFor)."""
    out = []
    mine = task.assignee_id == user.id
    approver = can_approve(user, task, wf)

    def add(key, label, fields=(), primary=False, danger=False, intro=""):
        out.append({"key": key, "label": label, "fields": list(fields), "primary": primary, "danger": danger, "intro": intro})

    if mine:
        if status == WS.NEW:
            if wf.days:
                add("accept", _("Accept · %(n)s d.") % {"n": wf.days}, primary=True)
                add("accept_own", _("I need a different term"), [F_DAYS, F_NOTE],
                    intro=_("The GIP will confirm the term; it counts from that day."))
            else:
                add("accept_own", _("Accept and name the term"), [F_DAYS, F_NOTE], primary=True,
                    intro=_("The GIP will confirm the term; it counts from that day."))
        if status in (WS.IN_PROGRESS, WS.REVISION):
            add("submit", _("Submit the work"), [("src", "check", _("Source files (DWG etc.) handed over"), False), F_NOTE],
                primary=True)
            add("to_appr", _("Send for approval"), [("what", "textarea", _("What needs approval"), True)],
                intro=_("While approval is going on, the term is paused and does not count against you."))
            add("question", _("Ask a question"), [("q", "textarea", _("Question"), True)])
    if approver:
        if status == WS.DRAFT:
            add("issue_tz", _("Issue the brief"), [("tz", "textarea", _("Brief: file link or task text"), False),
                                                  ("days", "number", _("Term, days (empty: the assignee names it)"), False)],
                primary=True, intro=_("The assignee will see the task in «My work» and accept it."))
        if status == WS.DAYS_PROPOSED:
            add("approve_days", _("Confirm the term · %(n)s d.") % {"n": wf.days or "—"}, primary=True)
            add("change_days", _("Set another term"), [F_DAYS])
            add("reject_days", _("Do not confirm"), [("why", "textarea", _("Why (the assignee will see it)"), True)])
        if status == WS.APPROVAL:
            add("appr_ok", _("Approved"), primary=True)
            add("appr_remarks", _("Has remarks"), [("why", "textarea", _("Remarks (the assignee will see them)"), True)])
            if wf.approver_kind != "Заказчик":
                add("appr_client", _("Take it to the client for approval"))
        if status == WS.QUESTION:
            add("answer", _("Answer"), [("a", "textarea", _("Answer"), True)], primary=True,
                intro=_last_log(task, "Есть вопрос"))
        if status == WS.REVIEW:
            add("review_ok", _("Accept the work"), primary=True)
            add("review_back", _("Send back for revision"), [("why", "textarea", _("What to fix (the assignee will see it)"), True)],
                danger=True, intro=_("A revision counts in the assignee's KPI."))
    return out


def _last_log(task, prefix):
    rep = ProgressReport.objects.filter(task=task, comment__startswith=f"▶ {prefix}").order_by("-created_at").first()
    if rep is None:
        return ""
    text = rep.comment.split(":", 1)[-1].rsplit(" · ", 1)[0].strip()
    return f"{prefix}: {text}"


def _next_step(task, wf, status, plan):
    days_left = (plan - today()).days if plan else None
    if status == WS.DRAFT:
        return _("Waiting for the brief from the GIP. This is a plan: work has not started yet.")
    if status == WS.NEW:
        if wf.days:
            return _("The brief is issued. Accept the task: the term is %(n)s d. from acceptance.") % {"n": wf.days}
        return _("The brief is issued. Accept the task and name your term.")
    if status == WS.DAYS_PROPOSED:
        return _("Term of %(n)s d. proposed. Waiting for the GIP to confirm.") % {"n": wf.days or "—"}
    if status == WS.APPROVAL:
        if wf.approver_kind == "Заказчик":
            return _("On approval with the client (handled by the GIP). The term is paused.")
        return _("On approval with the GIP. The term is paused.")
    if status == WS.QUESTION:
        return _("The question went to the GIP. Keep working, the answer will appear here.")
    if status == WS.REVIEW:
        return _("The work is submitted. Waiting for the GIP to accept it.")
    if status == WS.REVISION:
        return _("Sent back for revision. Fix it and submit again.")
    if status == WS.IN_PROGRESS:
        if days_left is None:
            return _("In progress.")
        if days_left < 0:
            return _("Overdue by %(n)s d. Submit as soon as possible.") % {"n": -days_left}
        if days_left == 0:
            return _("Due today.")
        return _("%(n)s d. left. Report the percentage every day.") % {"n": days_left}
    if status == WS.ACCEPTED:
        return _("Accepted.")
    return ""


def _history(task):
    out = []
    for r in ProgressReport.objects.filter(task=task).select_related("author").order_by("-created_at")[:15]:
        text = r.comment or ""
        is_status = text.startswith("▶")
        if is_status:
            text = text[1:].strip()
        else:
            pct = f"{round((r.done or 0) * 100)}%"
            note = text.split(":", 1)[1].strip() if text.startswith("Отчёт:") else ""
            text = f"{_('report')} {pct}" + (f" — {note}" if note else "")
        out.append({"date": r.date, "text": text, "status": is_status})
    return out


def task_card(user, task):
    wf = ensure_workflow(task)
    status = effective_status(task, wf)
    m = task_metrics(task, wf, status, PultSettings.load())
    plan = m["plan"]
    overdue = bool(plan and plan < today() and status in ACTIVE)
    problem = ""
    if m["control"] == "ТРЕВОГА 70%":
        problem = _("Alarm 70%")
    elif overdue:
        problem = _("Overdue")
    elif m["control"] == "Отстаёт":
        problem = _("Behind schedule")
    section = PlanRow.objects.filter(pk=wf.section).first() if wf.section else None
    reported = ProgressReport.objects.filter(task=task, date=today()).exclude(comment__startswith="▶").exists()
    return {
        "wf": wf,
        "status": status,
        "status_label": STATUS_LABELS.get(status, status),
        "status_tone": STATUS_TONE.get(status, "badge-default"),
        "next_step": _next_step(task, wf, status, plan),
        "actions": _actions(user, task, wf, status),
        "plan": plan,
        "days_left": (plan - today()).days if plan and status not in CLOSED else None,
        "started": status not in NOT_STARTED,
        "done_pct": round((wf.done or 0) * 100),
        "elapsed_pct": round(m["elapsed"] * 100) if m["elapsed"] is not None else None,
        "control": m["control"],
        "problem": problem,
        "overdue": overdue,
        "points": m["points"],
        "delay": m["delay"],
        "section_row": section,
        "approver": _approver_for(task),
        "history": _history(task),
        "can_report": task.assignee_id == user.id and status in ACTIVE,
        "reported_today": reported,
    }
