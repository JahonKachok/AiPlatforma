"""Dispetcher zadach: Pult vazifalarini Telegram tugmalari orqali boshqarish.

Bu modul faqat Django funksiyalaridan iborat (bot jarayoni ularni
``sync_to_async`` bilan chaqiradi), shuning uchun to'liq test qilinadi.
Barcha holat o'tishlari Pult'ning o'z ``run_action`` / ``send_report``
funksiyalari orqali — rol va holat tekshiruvi saytdagi bilan bir xil.

Callback formati (Telegram 64 bayt chegarasi): ``pd:<amal>:<№>[:<qiymat>]``
  a — qabul qilish (muddat bor)        o — o'z muddatini taklif qilish (kun)
  d — rad etish (sabab so'raladi)      p — kunlik foiz
  s — tekshiruvga topshirish           m — oraliq faylni keyinroq
"""
from dataclasses import dataclass, field
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.core.validators import AllowedExtensionsValidator
from apps.notifications.models import Notification
from apps.notifications.services import notify_user
from apps.telegram_bot.services import chat_language
from apps.telegram_bot.texts import t

from .models import PultSettings, TaskWorkflow
from .models import WorkflowStatus as WS
from .services import (
    ACTIVE, PultError, WorkCalendar, _approver_for, acts_as_assignee, effective_status, log_status,
    plan_date, run_action, send_report, task_metrics, today,
)

PERCENTS = (10, 25, 30, 45, 50, 70, 100)
OWN_DAYS = (3, 5, 7, 10, 15)
MID_FILE_AT = 0.5
FILE_LIMIT = 20 * 1024 * 1024  # bot Telegram'dan 20 MB gacha yuklab oladi
ALARM_TITLE = "Пульт: тревога №{n}"


@dataclass
class Reply:
    text: str
    buttons: list = field(default_factory=list)
    # Bot keyingi matn/faylni kutishi kerak bo'lsa: {"a": "decline"|"mid", "n": №}.
    wait: dict | None = None


def _lang(user):
    return chat_language(user.telegram_chat_id) if user and user.telegram_chat_id else "uz"


def user_by_chat(chat_id):
    return User.objects.filter(telegram_chat_id=str(chat_id), is_active=True).first()


# ---------------------------------------------------------------- tugmalar

def offer_buttons(wf, user):
    """Yangi vazifa: qabul / muddat taklifi / rad etish."""
    lang, n = _lang(user), wf.number
    if wf.days:
        first = [(t("pd.accept_days", lang, days=wf.days), f"pd:a:{n}")]
    else:
        first = [(t("pd.own_days", lang, days=d), f"pd:o:{n}:{d}") for d in OWN_DAYS]
    return [first, [(t("pd.decline", lang), f"pd:d:{n}")]]


def percent_buttons(wf, user=None):
    n = wf.number
    return [[(f"{p}%", f"pd:p:{n}:{p}") for p in PERCENTS[:4]], [(f"{p}%", f"pd:p:{n}:{p}") for p in PERCENTS[4:]]]


# ---------------------------------------------------------------- kiruvchi (bot)

def _wf(number):
    return TaskWorkflow.objects.select_related("task", "task__project").filter(number=number).first()


def _status_reply(lang, wf):
    wf.refresh_from_db()
    return Reply(t("pd.done", lang, n=wf.number, status=wf.status))


def handle_callback(chat_id, data):
    """Tugma bosilganda: holatni o'zgartiradi va javob matnini qaytaradi."""
    user = user_by_chat(chat_id)
    lang = chat_language(chat_id)
    if user is None:
        return Reply(t("pd.not_linked", lang))
    parts = data.split(":")
    if len(parts) < 3 or not parts[2].isdigit():
        return Reply(t("pd.expired", lang))
    action, number = parts[1], int(parts[2])
    value = parts[3] if len(parts) > 3 else ""
    try:
        if action == "a":
            _task, wf = run_action(user, number, "accept", {"expect_status": WS.NEW})
            return Reply(t("pd.done", lang, n=number, status=wf.status))
        if action == "o" and value.isdigit():
            _task, wf = run_action(user, number, "accept_own", {"days": int(value), "expect_status": WS.NEW})
            return Reply(t("pd.done", lang, n=number, status=wf.status))
        if action == "d":
            wf = _wf(number)
            if wf is None or effective_status(wf.task, wf) != WS.NEW or not acts_as_assignee(user, wf.task):
                return Reply(t("pd.expired", lang))
            return Reply(t("pd.ask_decline", lang, n=number), wait={"a": "decline", "n": number})
        if action == "p" and value.isdigit():
            return _report(user, lang, number, int(value))
        if action == "s":
            _task, wf = run_action(user, number, "submit", {})
            return Reply(t("pd.done", lang, n=number, status=wf.status))
        if action == "m":
            return Reply(t("pd.mid_later", lang))
    except PultError as exc:
        return Reply(f"⚠️ {exc.message}")
    return Reply(t("pd.expired", lang))


def _report(user, lang, number, pct):
    wf = _wf(number)
    if wf is None:
        return Reply(t("pd.expired", lang))
    before = wf.done
    send_report(user, [{"id": number, "done": pct}], "Telegram")
    reply = Reply(t("pd.report_saved", lang, n=number, pct=pct))
    if pct >= 100:
        reply.buttons = [[(t("pd.submit", lang), f"pd:s:{number}")]]
    elif pct / 100 >= MID_FILE_AT and not wf.mid_file_ok and (before < MID_FILE_AT or pct == 50):
        reply.text += "\n\n" + t("pd.ask_mid_file", lang, n=number)
        reply.buttons = [[(t("pd.later", lang), f"pd:m:{number}")]]
        reply.wait = {"a": "mid", "n": number}
    return reply


def handle_text(chat_id, wait, text):
    """Kutilgan matn (rad etish sababi) keldi."""
    user = user_by_chat(chat_id)
    lang = chat_language(chat_id)
    if user is None:
        return Reply(t("pd.not_linked", lang))
    if wait.get("a") != "decline":
        return Reply(t("pd.expired", lang))
    try:
        _task, wf = run_action(user, wait["n"], "decline", {"why": text.strip(), "expect_status": WS.NEW})
    except PultError as exc:
        return Reply(f"⚠️ {exc.message}")
    return Reply(t("pd.done", lang, n=wf.number, status=wf.status))


def handle_file(chat_id, wait, filename, data, mime_type=""):
    """Kutilgan oraliq fayl keldi: vazifa bo'limiga hujjat (reviziya) bo'lib
    tushadi — Arxivarius uni Drive'ga joylaydi."""
    from apps.documents.archivist import add_revision, find_same_file
    from apps.documents.models import AuditLog, Document, DocumentVersion

    user = user_by_chat(chat_id)
    lang = chat_language(chat_id)
    if user is None:
        return Reply(t("pd.not_linked", lang))
    wf = _wf(wait.get("n"))
    if wf is None or not acts_as_assignee(user, wf.task):
        return Reply(t("pd.expired", lang))
    try:
        AllowedExtensionsValidator()(ContentFile(b"", name=filename))
    except ValidationError:
        return Reply(t("pd.file_bad", lang))
    if len(data) > FILE_LIMIT:
        return Reply(t("pd.file_bad", lang))

    task = wf.task
    upload = ContentFile(bytes(data), name=filename)
    same = find_same_file(task.project, task.section, filename)
    if same is not None:
        add_revision(same, upload, user, notes=f"№{wf.number}: промежуточный файл")
        document = same
    else:
        document = Document.objects.create(
            name=f"№{wf.number} {task.title} — промежуточный"[:255], doc_type="intermediate",
            project=task.project, section=task.section, uploaded_by=user,
            file=upload, file_size=len(data), mime_type=mime_type or "",
        )
        DocumentVersion.objects.create(
            document=document, version_number=document.version,
            file=document.file.name, file_size=document.file_size, uploaded_by=user,
            notes=f"№{wf.number}: промежуточный файл",
        )
    AuditLog.log(obj=document, action="uploaded", user=user, details={"source": "telegram", "pult": wf.number})
    wf.mid_file_ok = True
    wf.save(update_fields=["mid_file_ok", "updated_at"])
    log_status(task, wf, user, f"Промежуточный файл: {filename}")
    approver = _approver_for(task)
    if approver is not None and approver.id != user.id:
        notify_user(approver, "task", f"№{wf.number}: промежуточный файл",
                    f"«{task.title}»: {filename}", link=f"/documents/{document.pk}/")
    return Reply(t("pd.mid_saved", lang, n=wf.number, name=filename))


# ---------------------------------------------------------------- chiquvchi (Celery)

def _send(user, text, buttons):
    from apps.telegram_bot.services import send_message

    send_message(user.telegram_chat_id, text, parse_mode=None, buttons=buttons)


def ask_daily_reports(user, workflows):
    """Kunlik hisobot so'rovi: har vazifaga alohida xabar, foiz tugmalari bilan."""
    lang = _lang(user)
    for wf in workflows:
        _send(user, t("pd.report_ask", lang, n=wf.number, title=wf.task.title, pct=round(wf.done * 100)),
              percent_buttons(wf, user))


def alarm_level(task, wf, settings):
    """Trevoga darajasi: 70 — muddatning 70% o'tdi, ish 70% emas;
    50 — yarmi o'tdi, ish 50% emas; None — hammasi joyida."""
    metrics = task_metrics(task, wf, effective_status(task, wf), settings)
    elapsed = metrics["elapsed"]
    if elapsed is None:
        return None, metrics
    if elapsed >= 0.7 and wf.done < 0.7:
        return 70, metrics
    if elapsed >= 0.5 and wf.done < 0.5:
        return 50, metrics
    return None, metrics


def send_alarms():
    """Ish kunlari: orqada qolgan vazifalar ijrochisiga trevoga (kuniga bir marta,
    vazifa holati to'g'rilanmaguncha har kuni)."""
    day = today()
    if not WorkCalendar().is_work(day):
        return 0
    settings = PultSettings.load()
    since = timezone.now() - timedelta(hours=20)
    sent = 0
    for wf in (TaskWorkflow.objects.filter(status__in=ACTIVE, start_date__isnull=False, task__assignee__isnull=False)
               .select_related("task", "task__assignee", "task__project")):
        task, user = wf.task, wf.task.assignee
        if effective_status(task, wf) not in ACTIVE or not user.is_active:
            continue
        level, metrics = alarm_level(task, wf, settings)
        if level is None:
            continue
        title = ALARM_TITLE.format(n=wf.number)
        if Notification.objects.filter(user=user, title=title, created_at__gte=since).exists():
            continue
        lang = _lang(user)
        plan = plan_date(task, wf)
        text = t(f"pd.alarm_{level}", lang, n=wf.number, title=task.title, elapsed=round(metrics["elapsed"] * 100),
                 pct=round(wf.done * 100), plan=plan.strftime("%d.%m.%Y") if plan else "—")
        notify_user(user, "deadline", title, text, link=f"/tasks/{task.pk}/", send_telegram=False)
        if user.telegram_chat_id:
            _send(user, text, percent_buttons(wf, user))
        sent += 1
    return sent


# ---------------------------------------------------------------- KPI

def kpi_rules(lang="uz"):
    s = PultSettings.load()

    def fmt(x):
        return f"{x:+g}"

    return t("pd.kpi_rules", lang, early=fmt(s.points_early), ontime=fmt(s.points_ontime),
             late=fmt(s.points_late_big), late_days=s.late_days, clean=fmt(s.points_clean),
             rework=f"{s.points_per_rework:g}", missed=f"{s.points_per_missed:g}", missed_max=f"{s.missed_max:g}")


def kpi_table(day=None):
    """Oy bo'yicha reyting: [(user_id, ball, vazifalar soni)], ko'pdan kamga.
    Ball — oy ichida qabul qilingan vazifalar uchun Pult KPI formulasi."""
    day = day or today()
    start = day.replace(day=1)
    settings = PultSettings.load()
    totals = {}
    for wf in (TaskWorkflow.objects.filter(status=WS.ACCEPTED, finished_at__gte=start, finished_at__lte=day,
                                           task__assignee__isnull=False).select_related("task")):
        points = task_metrics(wf.task, wf, WS.ACCEPTED, settings)["points"]
        if points is None:
            continue
        pts, n = totals.get(wf.task.assignee_id, (0, 0))
        totals[wf.task.assignee_id] = (pts + points, n + 1)
    return sorted(((uid, p, n) for uid, (p, n) in totals.items()), key=lambda r: -r[1])


def kpi_summary(user, lang="uz", day=None):
    day = day or today()
    table = kpi_table(day)
    rank = next((i for i, row in enumerate(table, start=1) if row[0] == user.pk), None)
    points, tasks = (table[rank - 1][1], table[rank - 1][2]) if rank else (0, 0)
    head = t("pd.kpi", lang, month=day.strftime("%m.%Y"), points=f"{points:g}", tasks=tasks,
             rank=rank or "—", total=len(table) or "—")
    return head + "\n\n" + kpi_rules(lang)


def active_for(user):
    """Ijrochining faol vazifalari (bot /report buyrug'i uchun)."""
    return [
        wf for wf in TaskWorkflow.objects.filter(status__in=ACTIVE).filter(Q(task__assignee=user))
        .select_related("task", "task__project")
        if effective_status(wf.task, wf) in ACTIVE
    ]

