"""Финансы и договоры Pulta platformaning moliya modulida.

Operatsiya = ``finance.FinancialRecord`` (bitta valyuta) + ``OperationInfo``
(Pult maydonlari). Ijrochi bilan shartnoma platformadagi ``EmployeeContract``
bilan sinxron saqlanadi, shuning uchun xodim uni «Mening maoshim»da ko'radi.
"""
import re
from collections import defaultdict
from datetime import date

from django.db import IntegrityError, transaction
from django.db.models import Max, Sum

from apps.accounts.models import User
from apps.finance.models import (
    Account, ContractStatus, Currency, EmployeeContract, FinanceSettings, FinancialRecord, RecordCategory,
    RecordStatus, RecordType,
)
from apps.finance.permissions import can_manage_finance
from apps.projects.models import Project

from .models import Contract, OperationInfo
from .services import PultError, internal_project

MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
CATEGORIES = [
    "Оплата заказчика", "Оплата исполнителю", "Зарплата", "Налоги", "Аренда", "Офис", "Материалы",
    "Коммунальные", "Конвертация", "Перевод между проектами", "Прочее",
]
TO_PLATFORM_CATEGORY = {
    "Налоги": RecordCategory.TAX, "Аренда": RecordCategory.RENT, "Зарплата": RecordCategory.SALARY,
    "Офис": RecordCategory.SUPPLIES, "Материалы": RecordCategory.MATERIALS, "Коммунальные": RecordCategory.UTILITIES,
}
FROM_PLATFORM_CATEGORY = {
    RecordCategory.TAX: "Налоги", RecordCategory.RENT: "Аренда", RecordCategory.SALARY: "Зарплата",
    RecordCategory.SUPPLIES: "Офис", RecordCategory.MATERIALS: "Материалы", RecordCategory.UTILITIES: "Коммунальные",
    RecordCategory.OTHER: "Прочее",
}
METHODS = ["Наличные", "Перечисление"]
OPEN, CLOSED = "Открыт", "Закрыт"


def can_finance(user):
    return can_manage_finance(user)


def usd_rate():
    return FinanceSettings.get_solo().usd_rate or None


def cur_out(currency):
    return "сум" if currency == "UZS" else "USD"


def cur_in(value):
    return "UZS" if str(value or "").strip().lower() in ("сум", "uzs", "so'm") else "USD"


# ---------------------------------------------------------------- numbering

def ensure_op_info(record):
    try:
        return record.pult_info
    except OperationInfo.DoesNotExist:
        pass
    for _attempt in range(5):
        try:
            with transaction.atomic():
                number = (OperationInfo.objects.aggregate(m=Max("number"))["m"] or 0) + 1
                return OperationInfo.objects.create(record=record, number=number)
        except IntegrityError:
            existing = OperationInfo.objects.filter(record=record).first()
            if existing:
                return existing
    raise PultError("Операции не удалось присвоить номер, повторите.", 409)


def next_contract_code():
    numbers = [int(m.group(1)) for code in Contract.objects.values_list("code", flat=True) if (m := re.search(r"(\d+)$", code))]
    return "Д-" + str(max(numbers, default=0) + 1).zfill(3)


# ---------------------------------------------------------------- contracts

def contract_paid(contract):
    return contract.operations.exclude(record__status=RecordStatus.CANCELLED).aggregate(s=Sum("offset"))["s"] or 0


def sync_employee_contract(contract):
    """Ijrochi platforma xodimi bo'lsa, uning EmployeeContract'ini yangilaydi."""
    if contract.side != "Исполнитель" or contract.user_id is None:
        return
    paid = contract_paid(contract)
    values = {
        "user": contract.user, "project": contract.project, "amount": contract.amount, "currency": contract.currency,
        "paid": paid, "notes": f"{contract.code} · {contract.section} · {contract.note}"[:1000],
        "status": ContractStatus.ACTIVE if contract.status == OPEN else ContractStatus.COMPLETED,
    }
    ec = contract.employee_contract
    if ec is None:
        contract.employee_contract = EmployeeContract.objects.create(**values)
        contract.save(update_fields=["employee_contract"])
    else:
        for k, v in values.items():
            setattr(ec, k, v)
        ec.save()


def _user_by_name(name):
    users = list(User.objects.filter(is_active=True, full_name=str(name or "").strip())[:2])
    return users[0] if len(users) == 1 else None


def create_contract(project, code, data, source=""):
    try:
        amount = float(data.get("amount") or 0)
    except (TypeError, ValueError):
        raise PultError("Неверная сумма договора.")
    contract = Contract.objects.create(
        code=code, project=project, side=data.get("side") or "Исполнитель", name=str(data.get("name") or "")[:255],
        user=_user_by_name(data.get("name")), section=str(data.get("section") or "")[:50],
        currency=cur_in(data.get("cur")), amount=amount, note=str(data.get("note") or ""), source=source,
    )
    sync_employee_contract(contract)
    return contract


def update_contract(contract, changes):
    if set(changes) - {"amount", "note"}:
        raise PultError("Недопустимое изменение договора.")
    if "amount" in changes:
        try:
            contract.amount = float(changes["amount"] or 0)
        except (TypeError, ValueError):
            raise PultError("Неверная сумма договора.")
    if "note" in changes:
        contract.note = str(changes["note"] or "")
    contract.save()
    sync_employee_contract(contract)


def contracts_json(rate):
    paid = dict(
        OperationInfo.objects.exclude(contract=None).exclude(record__status=RecordStatus.CANCELLED)
        .values("contract").annotate(s=Sum("offset")).values_list("contract", "s")
    )
    out = []
    for c in Contract.objects.select_related("project"):
        p = paid.get(c.pk) or 0
        rest = c.amount - p
        out.append({
            "id": c.code, "project": c.project.name, "side": c.side, "name": c.name, "section": c.section,
            "cur": cur_out(c.currency), "amount": c.amount, "paid": p, "rest": rest,
            "restUsd": rest if c.currency == "USD" else (rest / rate if rate else None),
            "status": c.status, "note": c.note, "src": c.source,
        })
    return out


# ---------------------------------------------------------------- operations

def operations_json():
    records = (FinancialRecord.objects.exclude(status=RecordStatus.CANCELLED)
               .select_related("project", "created_by", "pult_info", "pult_info__contract"))
    out = []
    for r in records:
        info = ensure_op_info(r)
        signed = r.signed_amount
        out.append({
            "id": info.number, "date": r.date.isoformat(), "project": r.project.name, "who": info.counterparty or None,
            "type": "Приход" if signed >= 0 else "Расход",
            "cat": info.category or FROM_PLATFORM_CATEGORY.get(r.category, "") or None,
            "uzs": signed if r.currency == Currency.UZS else None, "usd": signed if r.currency == Currency.USD else None,
            "method": info.method or ("Наличные" if r.account == Account.USD_CASH else "Перечисление"),
            "contract": info.contract.code if info.contract_id else None, "offset": info.offset,
            "note": r.description or None, "by": r.created_by.full_name if r.created_by_id else None,
            "at": r.created_at.isoformat(),
        })
    return out


def _project(name, user):
    name = str(name or "").strip()
    if name == "GASTEC":
        found = list(Project.objects.filter(name=name)[:2])
        return found[0] if len(found) == 1 else internal_project(user)
    found = list(Project.objects.filter(name=name)[:2])
    if len(found) != 1:
        raise PultError(f"Проект «{name}» не найден или его имя не уникально.")
    return found[0]


def _amount(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise PultError("Неверная сумма.")


@transaction.atomic
def create_operations(user, rows):
    if not can_finance(user):
        raise PultError("Операции вносят руководитель или бухгалтер.", 403)
    if not isinstance(rows, list) or not rows:
        raise PultError("Нет операций.")
    rate = usd_rate()
    created, touched = [], set()
    for row in rows:
        try:
            day = date.fromisoformat(str(row.get("date"))[:10])
        except ValueError:
            raise PultError("Укажите дату.")
        project = _project(row.get("project"), user)
        contract = None
        if row.get("contract"):
            contract = Contract.objects.filter(code=row["contract"]).first()
            if contract is None or contract.project_id != project.pk:
                raise PultError(f"Договор {row['contract']} не относится к проекту «{project.name}».")
        cat = str(row.get("cat") or "")[:100]
        method = row.get("method") if row.get("method") in METHODS else "Перечисление"
        parts = [(Currency.UZS, _amount(row.get("uzs"))), (Currency.USD, _amount(row.get("usd")))]
        parts = [(cur, v) for cur, v in parts if v]
        if not parts:
            raise PultError("Впишите сумму в сумах или в долларах.")
        for i, (cur, value) in enumerate(parts):
            account = Account.UZS_BANK if cur == Currency.UZS else (Account.USD_CASH if method == "Наличные" else Account.USD_BANK)
            record = FinancialRecord.objects.create(
                project=project, type=RecordType.INCOME if value > 0 else RecordType.EXPENSE, account=account,
                amount=abs(value), currency=cur, exchange_rate=rate if cur == Currency.USD else None,
                description=str(row.get("note") or "")[:500] or None,
                category=TO_PLATFORM_CATEGORY.get(cat, RecordCategory.OTHER), date=day,
                status=RecordStatus.CONFIRMED, created_by=user,
            )
            info = ensure_op_info(record)
            info.counterparty, info.category, info.method = str(row.get("who") or "")[:255], cat, method
            if i == 0 and contract is not None:
                info.contract = contract
                info.offset = _amount(row.get("offset"))
                touched.add(contract.pk)
            info.save()
            created.append(info.number)
    for contract in Contract.objects.filter(pk__in=touched):
        sync_employee_contract(contract)
    return created


# ---------------------------------------------------------------- summary («Главная», «По месяцам»)

def summary_json(rate):
    records = list(FinancialRecord.objects.exclude(status=RecordStatus.CANCELLED).select_related("pult_info"))
    uzs = sum(r.signed_amount for r in records if r.currency == Currency.UZS)
    usd = sum(r.signed_amount for r in records if r.currency == Currency.USD)
    total = usd + (uzs / rate if rate else 0)

    contracts = contracts_json(rate)
    open_rest = lambda side: sum(max(0, c["restUsd"] or 0) for c in contracts if c["side"] == side and c["status"] == OPEN)  # noqa: E731
    owed = open_rest("Исполнитель")
    expected = open_rest("Заказчик")
    home = {
        "date": date.today().isoformat(), "rate": rate, "uzs": uzs, "usd": usd, "totalUsd": total,
        "profitHead": ["GASTEC", ""],
        "profit": [
            {"label": "Деньги сейчас, всего в $", "a": total, "b": None},
            {"label": "Ожидаем от заказчиков (открытые договоры)", "a": expected, "b": None},
            {"label": "Должны исполнителям", "a": owed, "b": None},
            {"label": "Чистая прибыль (прогноз)", "a": total + expected - owed, "b": None},
        ],
    }

    months = defaultdict(lambda: defaultdict(float))
    for r in records:
        key = r.date.strftime("%Y-%m")
        signed = r.signed_amount
        m = months[key]
        if r.currency == Currency.UZS:
            m["inUzs" if signed > 0 else "outUzs"] += abs(signed)
        else:
            m["inUsd" if signed > 0 else "outUsd"] += abs(signed)
        if signed < 0:
            eq = abs(signed) * (rate if r.currency == Currency.USD and rate else 1)
            cat = getattr(getattr(r, "pult_info", None), "category", "") or FROM_PLATFORM_CATEGORY.get(r.category, "")
            if cat == "Зарплата":
                m["salary"] += eq
            elif cat == "Налоги":
                m["taxes"] += eq
            elif cat in ("Офис", "Аренда", "Коммунальные"):
                m["office"] += eq
    month_rows = [
        {"month": f"{MONTHS[int(k[5:]) - 1]} {k[:4]}", **{f: v.get(f, 0) for f in ("inUzs", "outUzs", "inUsd", "outUsd", "salary", "taxes", "office")}}
        for k, v in sorted(months.items(), reverse=True)
    ]
    return home, month_rows, contracts


def finance_payload(user):
    if not can_finance(user):
        return {}
    rate = usd_rate()
    home, months, contracts = summary_json(rate)
    return {
        "ops": operations_json(), "contracts": contracts, "home": home, "months": months, "rate": rate,
        "lists": {"types": ["Приход", "Расход"], "cats": CATEGORIES, "methods": METHODS, "sides": ["Исполнитель", "Заказчик", "Налог"]},
    }
