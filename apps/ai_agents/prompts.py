"""Orchestrator va 9 ta agentning tizim promptlari hamda JSON chiqish sxemalari.

Token tejash qoidalari (Claude API, kichik test byudjeti):
- Promptlar inglizcha va qisqa: model ularni yaxshi tushunadi, token kam.
- Har agent faqat qat'iy JSON qaytaradi (output_config.format) — erkin matn,
  tushuntirish yoki «salom» yo'q; foydalanuvchiga matnni Python o'zi yozadi.
- Kontekst (loyihalar ro'yxati, sana) minimal; foydalanuvchi tuzatishlari
  (AgentMemory) promptning oxiriga «User rules» bo'lib qo'shiladi.
- Ko'p xabarlar LLM'siz, kalit so'zlar bilan yo'naltiriladi (orchestrator.py).

Ishchi kompyuterdagi agentlar (tarjimon, pechatnik/shtamp, normokontrol,
sekretar) shu sxemalar bilan 5-bosqichda lokal worker orqali ishlaydi.
"""

ORCHESTRATOR = (
    "Route a message from a design/construction company employee to one agent. "
    "Agents: dispatcher (tasks, progress, deadlines), kpi (points, rating), "
    "treasurer (project money in/out), quartermaster (office costs: salary, rent, furniture, "
    "stationery, inventory, repair, utilities, tax), translator (translate DWG/XLSX/PDF text zh/ru/en), "
    "printer (DWG->PDF, title block stamp), norm_control (check drawings), "
    "archivist (find/send/zip project files, revisions), secretary (letters, contracts, signature/seal), "
    "chat (anything else). Reply JSON only."
)
ORCHESTRATOR_SCHEMA = {
    "type": "object",
    "properties": {
        "agent": {"type": "string", "enum": [
            "dispatcher", "kpi", "treasurer", "quartermaster", "translator", "printer",
            "norm_control", "archivist", "secretary", "chat",
        ]},
    },
    "required": ["agent"],
    "additionalProperties": False,
}

# --- 3/4. Kaznachey va Zavxoz: bitta chaqiruv, scope bo'yicha ajraladi ---------

PROJECT_CATEGORIES = [
    "Оплата заказчика", "Оплата исполнителю", "Зарплата", "Налоги", "Аренда", "Офис", "Материалы",
    "Коммунальные", "Конвертация", "Перевод между проектами", "Прочее",
]
OFFICE_CATEGORIES = ["salary", "rent", "furniture", "stationery", "inventory", "repair", "utilities", "tax", "other"]

FINANCE = (
    "Extract ONE money operation from the boss's message (uz/ru/en, may be a voice transcript). "
    "scope=project if it belongs to a client project (payment to a contractor/engineer, from a customer); "
    "scope=office for internal company costs (salary, rent, furniture, stationery, inventory, repair, "
    "utilities, tax) not tied to a project; scope=none if it is not a money operation. "
    "direction: in = money received, out = paid/sent. amount: positive number as said "
    "('50 dollar'=50 USD, '2 mln'=2000000, 'ming'=thousand). currency USD or UZS (so'm/сум). "
    "project: exact name from the list or '' if not said. counterparty: who paid/received ('' if none). "
    "method: cash or transfer (default transfer). date: YYYY-MM-DD, relative to today ('bugun', 'вчера'), "
    "'' = today. period for office costs: month (salary, rent, utilities), quarter, year, or once. "
    "note: short, in the message language. Reply JSON only."
)
FINANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "scope": {"type": "string", "enum": ["project", "office", "none"]},
        "direction": {"type": "string", "enum": ["in", "out"]},
        "amount": {"type": "number"},
        "currency": {"type": "string", "enum": ["USD", "UZS"]},
        "project": {"type": "string"},
        "counterparty": {"type": "string"},
        "project_category": {"type": "string", "enum": PROJECT_CATEGORIES},
        "office_category": {"type": "string", "enum": OFFICE_CATEGORIES},
        "method": {"type": "string", "enum": ["cash", "transfer"]},
        "date": {"type": "string"},
        "period": {"type": "string", "enum": ["month", "quarter", "year", "once"]},
        "note": {"type": "string"},
    },
    "required": ["scope", "direction", "amount", "currency", "project", "counterparty", "project_category",
                 "office_category", "method", "date", "period", "note"],
    "additionalProperties": False,
}

# --- 8. Arxivarius: «Falonchiga falon obyekt razdellarini ZIP qilib tashla» ----

ARCHIVIST = (
    "Extract a file-sending request. project: name from the list ('' if not said). "
    "object: building/object name ('' = whole project). discipline: code like AR, KJ, OV, VK, EOM ('' = all). "
    "recipient: person's name ('' = the sender himself). Reply JSON only."
)
ARCHIVIST_SCHEMA = {
    "type": "object",
    "properties": {
        "project": {"type": "string"},
        "object": {"type": "string"},
        "discipline": {"type": "string"},
        "recipient": {"type": "string"},
    },
    "required": ["project", "object", "discipline", "recipient"],
    "additionalProperties": False,
}

# --- 1. Dispetcher va 2. KPI — LLM'siz (Pult tugmalari, apps/pult/dispatcher.py) -

DISPATCHER = (
    "Extract a task progress report. task: task number (integer, 0 if unknown). "
    "percent: 0-100 or -1 if not said. question: employee's question or ''. Reply JSON only."
)
DISPATCHER_SCHEMA = {
    "type": "object",
    "properties": {
        "task": {"type": "integer"}, "percent": {"type": "integer"}, "question": {"type": "string"},
    },
    "required": ["task", "percent", "question"],
    "additionalProperties": False,
}
KPI = "KPI is computed by fixed rules in code; no LLM call."

# --- 5-7, 9. Ishchi kompyuter agentlari (5-bosqich: lokal worker) -------------

TRANSLATOR = (
    "Translate CAD/Excel/PDF strings between zh, ru, en. Input: JSON list of {id, text, max_len}. "
    "Keep numbers, units, codes, axis marks and abbreviations (e.g. 'М1:100', 'Ø20', 'A-1') unchanged. "
    "Never exceed max_len characters (shorten wording, never overflow the frame). "
    "Do not translate file names. Reply JSON only."
)
TRANSLATOR_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
        "required": ["id", "text"], "additionalProperties": False,
    }}},
    "required": ["items"],
    "additionalProperties": False,
}

PRINTER = (
    "Fill a drawing title block. Input: block attribute tags and project data "
    "(cipher, discipline, sheet, executor, GIP, date). Map each tag to a value; unknown -> ''. "
    "Keep text short enough for its field. Reply JSON only."
)
PRINTER_SCHEMA = {
    "type": "object",
    "properties": {"fields": {"type": "array", "items": {
        "type": "object",
        "properties": {"tag": {"type": "string"}, "value": {"type": "string"}},
        "required": ["tag", "value"], "additionalProperties": False,
    }}},
    "required": ["fields"],
    "additionalProperties": False,
}

NORM_CONTROL = (
    "You check a drawing set against drafting standards. Input: machine-extracted facts per sheet "
    "(overlapping text boxes, frame size, missing title-block fields, layer/scale data). "
    "Return only real problems as remarks; severity: critical (blocks issue) or minor. "
    "Be terse, in Russian. Reply JSON only."
)
NORM_CONTROL_SCHEMA = {
    "type": "object",
    "properties": {"remarks": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "sheet": {"type": "string"}, "issue": {"type": "string"},
            "severity": {"type": "string", "enum": ["critical", "minor"]},
        },
        "required": ["sheet", "issue", "severity"], "additionalProperties": False,
    }}},
    "required": ["remarks"],
    "additionalProperties": False,
}

SECRETARY = (
    "Draft an official letter or contract body for a design company on its letterhead template. "
    "Input: kind, addressee, subject, key points, language. Formal business style, no placeholders "
    "left unfilled except dates/numbers you were not given (use '___'). The signature line must read "
    "'Директор' exactly once. Reply JSON only."
)
SECRETARY_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"}, "addressee": {"type": "string"},
        "body": {"type": "string"}, "signature_label": {"type": "string"},
    },
    "required": ["title", "addressee", "body", "signature_label"],
    "additionalProperties": False,
}

# Reyestr: kalit -> (prompt, sxema, ishlaydigan joy)
AGENTS = {
    "orchestrator": (ORCHESTRATOR, ORCHESTRATOR_SCHEMA, "server"),
    "dispatcher": (DISPATCHER, DISPATCHER_SCHEMA, "server"),
    "kpi": (KPI, None, "server"),
    "treasurer": (FINANCE, FINANCE_SCHEMA, "server"),
    "quartermaster": (FINANCE, FINANCE_SCHEMA, "server"),
    "translator": (TRANSLATOR, TRANSLATOR_SCHEMA, "worker"),
    "printer": (PRINTER, PRINTER_SCHEMA, "worker"),
    "norm_control": (NORM_CONTROL, NORM_CONTROL_SCHEMA, "worker"),
    "archivist": (ARCHIVIST, ARCHIVIST_SCHEMA, "server"),
    "secretary": (SECRETARY, SECRETARY_SCHEMA, "worker"),
}
