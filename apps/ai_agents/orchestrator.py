"""Orchestrator (AI Router): Telegram xabarini kerakli agentga yo'naltiradi.

Token tejash tartibi:
1. Kalit so'zlar (0 token): pul + summa -> Kaznachey/Zavxoz, «zip / tashlab ber»
   -> Arxivarius, «kpi / reyting» -> KPI, «eslab qol» -> xotira.
2. Mos agent bo'lsa — bitta qisqa LLM chaqiruvi, qat'iy JSON (prompts.py).
3. Bajarishni Python qiladi; pul yozuvlari foydalanuvchi tasdig'idan keyin.
4. Hech biriga tushmagan xabar — None: bot oddiy AI chat'ga (answer_telegram) beradi.
"""
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db.models import Q, Sum
from django.utils import timezone

from apps.telegram_bot.texts import t

from . import prompts
from .models import AgentMemory, PendingAction
from .services import ask_json

PENDING_TTL = timedelta(hours=24)
MEMORY_LIMIT = 8

_AMOUNT = re.compile(r"\d")
_MONEY = re.compile(
    r"(\$|доллар|dollar|so['ʻ’]?m\b|сум|сўм|usd|uzs|o['ʻ’]?tkaz|to['ʻ’]?la|berdim|oldim|tushdi|kirim|chiqim|"
    r"xarajat|перев|оплат|заплат|получил|поступ|расход|приход|ijara|аренд|zarplata|maosh|зарплат|"
    r"kanselyar|канцел|mebel|мебел|remont|ta['ʻ’]?mir|ремонт|inventar|инвентар|kommunal|коммунал|soliq|налог)",
    re.I,
)
_OFFICE = re.compile(
    r"(ofis|офис|ijara|аренд|zarplata|maosh|oylik|зарплат|kanselyar|канцел|mebel|мебел|remont|ta['ʻ’]?mir|"
    r"ремонт|inventar|инвентар|kommunal|коммунал|soliq|налог|svet|elektr|internet)",
    re.I,
)
_ARCHIVE = re.compile(r"(\bzip\b|архив|arxiv|tashlab ber|скинь|отправь .*(раздел|чертеж|файл)|razdel)", re.I)
_KPI = re.compile(r"(\bkpi\b|reyting|рейтинг|ballarim|мои баллы|\bball\b)", re.I)
_MEMORY = re.compile(r"^\s*(eslab qol\w*|esla\w*|запомни\w*|remember)\s*[:,-]?\s*(?P<text>.+)$", re.I | re.S)
# Tuzatish qaysi agentga tegishli (bo'lmasa — hammasiga).
_MEMORY_AGENT = [
    ("translator", r"tarjim|перев|translat|matn|текст|шрифт|shrift"),
    ("printer", r"pdf|shtamp|штамп|печат|ramka|рамк"),
    ("norm_control", r"normo|нормо|tekshir|провер"),
    ("secretary", r"xat|письм|shartnom|договор|imzo|подпис|muhr|печать"),
    ("treasurer", r"pul|so['ʻ’]?m|dollar|оплат|kirim|chiqim"),
    ("quartermaster", r"ofis|ijara|zarplata|офис|аренд"),
]
WORKER_AGENTS = {"translator", "printer", "norm_control", "secretary"}
_WORKER = [
    ("translator", re.compile(r"(tarjima qil|переведи|translate)", re.I)),
    ("printer", re.compile(r"(pdf ga|pdf qil|в pdf|to pdf|shtamp|штамп)", re.I)),
    ("norm_control", re.compile(r"(normokontrol|нормоконтрол|norm control)", re.I)),
    ("secretary", re.compile(r"(xat tayyorla|shartnoma tayyorla|подготовь (письмо|договор)|draft a (letter|contract))", re.I)),
]

OFFICE_STORE = {  # Zavxoz toifasi -> AdministrativeExpense.category
    "rent": "rent", "stationery": "supplies", "utilities": "utilities", "tax": "tax", "other": "other",
    "salary": "Зарплата", "furniture": "Мебель", "inventory": "Инвентарь", "repair": "Ремонт",
}
RECURRING = {"salary": "month", "rent": "month", "utilities": "month", "tax": "quarter"}


@dataclass
class Reply:
    text: str
    buttons: list = field(default_factory=list)
    html: bool = False


# ---------------------------------------------------------------- yordamchilar

def _memory_rules(user, agent):
    rows = (AgentMemory.objects.filter(Q(user=user) | Q(user__isnull=True), agent__in=[agent, "*"])
            .values_list("text", flat=True)[:MEMORY_LIMIT])
    return ("\nUser rules (always apply):\n- " + "\n- ".join(rows)) if rows else ""


def _projects(user, limit=40):
    from apps.projects.permissions import visible_projects_for

    return list(visible_projects_for(user).exclude(status="completed").order_by("-created_at")
                .values_list("name", flat=True)[:limit])


def _context(user, text):
    names = "; ".join(n[:40] for n in _projects(user))
    return f"today={timezone.localdate().isoformat()}\nprojects: {names or '-'}\nmessage: {text[:1500]}"


def _find_project(user, name):
    from apps.projects.permissions import visible_projects_for

    name = (name or "").strip()
    if not name:
        return None
    qs = visible_projects_for(user)
    exact = list(qs.filter(name__iexact=name)[:2])
    if len(exact) == 1:
        return exact[0]
    found = list(qs.filter(name__icontains=name)[:2])
    return found[0] if len(found) == 1 else None


def _fmt(amount, currency):
    return f"{amount:,.2f}".rstrip("0").rstrip(".").replace(",", " ") + (" USD" if currency == "USD" else " so'm")


def _confirm_buttons(lang, pending):
    return [[(t("ag.confirm", lang), f"ag:ok:{pending.pk}"), (t("ag.cancel", lang), f"ag:no:{pending.pk}")]]


def _date(value):
    try:
        return date.fromisoformat((value or "")[:10])
    except ValueError:
        return timezone.localdate()


# ---------------------------------------------------------------- kirish nuqtasi

def route(text):
    """Kalit so'zlar bo'yicha agent (LLM'siz). None — oddiy chat."""
    if _MEMORY.match(text):
        return "memory"
    if _KPI.search(text):
        return "kpi"
    if _AMOUNT.search(text) and _MONEY.search(text):
        return "quartermaster" if _OFFICE.search(text) else "treasurer"
    if _ARCHIVE.search(text):
        return "archivist"
    for agent, rx in _WORKER:
        if rx.search(text):
            return agent
    return None


def handle(user, text, lang="uz"):
    """Xabarni agent bajaradi -> Reply; agentga tegishli bo'lmasa None (chat)."""
    text = (text or "").strip()
    agent = route(text)
    if agent is None:
        return None
    if agent == "memory":
        return _remember(user, lang, _MEMORY.match(text).group("text"))
    if agent == "kpi":
        from apps.pult.dispatcher import kpi_summary

        return Reply(kpi_summary(user, lang), html=True)
    if agent in ("treasurer", "quartermaster"):
        return _finance(user, lang, text, agent)
    if agent == "archivist":
        return _archive(user, lang, text)
    return _worker(user, lang, text, agent)


def _remember(user, lang, text):
    agent = next((a for a, rx in _MEMORY_AGENT if re.search(rx, text, re.I)), "*")
    AgentMemory.objects.create(user=user, agent=agent, text=text.strip()[:500])
    return Reply(t("ag.remembered", lang))


# ---------------------------------------------------------------- Kaznachey / Zavxoz

def _finance(user, lang, text, agent):
    from apps.finance.permissions import can_manage_finance

    if not can_manage_finance(user):
        return Reply(t("ag.finance_denied", lang))
    data = ask_json(prompts.FINANCE + _memory_rules(user, agent), _context(user, text),
                    prompts.FINANCE_SCHEMA, agent=agent, max_tokens=600)
    if not data:
        return Reply(t("ag.not_understood", lang))
    if data["scope"] == "none" or not data["amount"] or data["amount"] <= 0:
        return None  # pul amali emas — oddiy chat javob bersin
    sign = "+" if data["direction"] == "in" else "−"
    money = _fmt(float(data["amount"]), data["currency"])
    day = _date(data["date"])
    if data["scope"] == "office":
        pending = PendingAction.objects.create(user=user, kind="office_expense", payload=data)
        summary = t("ag.office_summary", lang, money=money, cat=data["office_category"],
                    who=data["counterparty"] or "—", date=day.strftime("%d.%m.%Y"), note=data["note"] or "—")
        return Reply(summary, _confirm_buttons(lang, pending))
    project = _find_project(user, data["project"])
    if project is None:
        return Reply(t("ag.project_unknown", lang, name=data["project"] or "—"))
    data["project"] = project.name
    pending = PendingAction.objects.create(user=user, kind="project_operation", payload=data)
    summary = t("ag.project_summary", lang, sign=sign, money=money, project=project.name,
                who=data["counterparty"] or "—", cat=data["project_category"], date=day.strftime("%d.%m.%Y"))
    return Reply(summary, _confirm_buttons(lang, pending))


def _project_balance(project):
    from apps.finance.models import FinancialRecord, RecordStatus, RecordType

    out = []
    for cur in ("UZS", "USD"):
        qs = FinancialRecord.objects.filter(project=project, currency=cur).exclude(status=RecordStatus.CANCELLED)
        income = qs.filter(type=RecordType.INCOME).aggregate(s=Sum("amount"))["s"] or 0
        spent = qs.exclude(type=RecordType.INCOME).aggregate(s=Sum("amount"))["s"] or 0
        if income or spent:
            out.append(_fmt(income - spent, cur))
    return ", ".join(out) or "0"


def _execute(pending):
    """Tasdiqlangan amalni bajaradi, natija matnini qaytaradi."""
    from apps.finance.models import AdministrativeExpense, FinanceCategory
    from apps.pult.finance import create_operations

    data, user = pending.payload, pending.user
    day = _date(data["date"])
    if pending.kind == "project_operation":
        value = float(data["amount"]) * (1 if data["direction"] == "in" else -1)
        row = {
            "date": day.isoformat(), "project": data["project"], "who": data["counterparty"],
            "cat": data["project_category"], "method": "Наличные" if data["method"] == "cash" else "Перечисление",
            "note": data["note"], ("usd" if data["currency"] == "USD" else "uzs"): value,
        }
        numbers = create_operations(user, [row])
        from apps.projects.models import Project

        project = Project.objects.get(name=data["project"])
        return "project_saved", {"n": numbers[0], "project": project.name, "balance": _project_balance(project)}
    cat = data["office_category"]
    stored = OFFICE_STORE.get(cat, "other")
    if stored not in ("rent", "supplies", "utilities", "tax", "other"):
        FinanceCategory.objects.get_or_create(name=stored, type="admin", defaults={"created_by": user})
    period = data["period"] if data["period"] in ("month", "quarter", "year") else RECURRING.get(cat, "month")
    note = " · ".join(x for x in (data["counterparty"], data["note"], "Telegram") if x)
    AdministrativeExpense.objects.create(
        category=stored, amount=float(data["amount"]), currency=data["currency"], period=period,
        date=day, note=note[:500], created_by=user,
    )
    return "office_saved", {"money": _fmt(float(data["amount"]), data["currency"]), "cat": stored}


def confirm(user, data, lang="uz"):
    """Tugma «ag:ok:<id>» / «ag:no:<id>»."""
    from apps.pult.services import PultError

    parts = data.split(":")
    if len(parts) != 3 or user is None:
        return Reply(t("pd.expired", lang))
    pending = PendingAction.objects.filter(
        pk=parts[2] if re.fullmatch(r"[0-9a-f-]{36}", parts[2]) else None, user=user, done_at__isnull=True,
        created_at__gte=timezone.now() - PENDING_TTL,
    ).first()
    if pending is None:
        return Reply(t("pd.expired", lang))
    pending.done_at = timezone.now()
    pending.save(update_fields=["done_at"])
    if parts[1] != "ok":
        return Reply(t("ag.cancelled", lang))
    try:
        key, fmt = _execute(pending)
    except PultError as exc:
        return Reply(f"⚠️ {exc.message}")
    return Reply(t(f"ag.{key}", lang, **fmt))


# ---------------------------------------------------------------- Arxivarius

def _archive(user, lang, text):
    from apps.accounts.models import User
    from apps.documents.models import Document
    from apps.documents.tasks import send_documents_to_telegram

    data = ask_json(prompts.ARCHIVIST + _memory_rules(user, "archivist"), _context(user, text),
                    prompts.ARCHIVIST_SCHEMA, agent="archivist", max_tokens=300)
    if not data:
        return Reply(t("ag.not_understood", lang))
    project = _find_project(user, data["project"])
    if project is None:
        return Reply(t("ag.project_unknown", lang, name=data["project"] or "—"))
    docs = Document.objects.filter(project=project).exclude(file="").exclude(file__isnull=True)
    if data["object"]:
        o = data["object"]
        docs = docs.filter(Q(section__sub_object__name__icontains=o) | Q(section__sub_object__parent__name__icontains=o))
    if data["discipline"]:
        docs = docs.filter(section__discipline__code__iexact=data["discipline"])
    ids = [str(pk) for pk in docs.values_list("pk", flat=True)[:500]]
    if not ids:
        return Reply(t("ag.no_files", lang))
    recipient = user
    if data["recipient"]:
        found = list(User.objects.filter(is_active=True, full_name__icontains=data["recipient"])[:2])
        if len(found) != 1:
            return Reply(t("ag.recipient_unknown", lang, name=data["recipient"]))
        recipient = found[0]
    if not recipient.telegram_chat_id:
        return Reply(t("ag.recipient_no_tg", lang, name=recipient.full_name))
    send_documents_to_telegram.delay(str(user.pk), str(recipient.pk), ids)
    return Reply(t("ag.files_sending", lang, count=len(ids), name=recipient.full_name))


# ---------------------------------------------------------------- Ishchi kompyuter agentlari

MAX_JOBS = 30


def _worker(user, lang, text, agent):
    """Tarjimon / Pechatnik-Shtampovshik / Normokontrol — fayllar uchun ish
    navbatga qo'yiladi; Sekretar — xat qoralamasi (secretary.py)."""
    from apps.documents.services import file_basename
    from apps.worker.models import JobKind
    from apps.worker.services import accepts, create_job, is_online

    if agent == "secretary":
        from .secretary import draft

        return draft(user, text, lang)
    data = ask_json(prompts.WORKER_REQUEST + _memory_rules(user, agent), _context(user, text),
                    prompts.WORKER_REQUEST_SCHEMA, agent=agent, max_tokens=300)
    if not data:
        return Reply(t("ag.not_understood", lang))
    project = _find_project(user, data["project"])
    if project is None:
        return Reply(t("ag.project_unknown", lang, name=data["project"] or "—"))
    if agent == "translator" and not data["target_lang"]:
        return Reply(t("ag.which_lang", lang))
    docs = project.documents.exclude(file="").exclude(file__isnull=True)
    if data["object"]:
        o = data["object"]
        docs = docs.filter(Q(section__sub_object__name__icontains=o) | Q(section__sub_object__parent__name__icontains=o))
    if data["discipline"]:
        docs = docs.filter(section__discipline__code__iexact=data["discipline"])
    if data["file"]:
        docs = docs.filter(Q(original_name__icontains=data["file"]) | Q(name__icontains=data["file"]))
    kinds = {
        "translator": (JobKind.DWG_TRANSLATE, JobKind.XLSX_TRANSLATE),
        "printer": (JobKind.DWG_PRINT,),
        "norm_control": (JobKind.NORM_CONTROL,),
    }[agent]
    created = 0
    for doc in docs[:200]:
        kind = next((k for k in kinds if accepts(k, file_basename(doc))), None)
        if kind is None or not doc.versions.exists():
            continue
        create_job(kind, doc, user, params={"target_lang": data["target_lang"]} if agent == "translator" else {})
        created += 1
        if created >= MAX_JOBS:
            break
    if not created:
        return Reply(t("ag.no_files", lang))
    return Reply(t("ag.jobs_queued" if is_online() else "ag.jobs_queued_offline", lang, count=created))
