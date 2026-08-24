from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.projects.models import Project, SubObject
from apps.projects.permissions import can_edit_project, visible_projects_for
from apps.reports.exports import build_cash_flow_workbook

import datetime
import json
import uuid

from .forms import (
    AdministrativeExpenseForm,
    EmployeeContractForm,
    EmployeeContractPayForm,
    FinanceCategoryForm,
    FinancialRecordForm,
    TransactionForm,
)
from .models import (
    ACCOUNT_CURRENCY,
    Account,
    AdminExpenseCategory,
    AdministrativeExpense,
    Currency,
    EmployeeContract,
    FinanceCategory,
    FinanceSettings,
    FinancialRecord,
    RecordCategory,
    RecordStatus,
    RecordType,
)
from .services import fetch_usd_rate, fetch_usd_rate_poytaxtbank

_CAN_MANAGE_FINANCE_ROLES = {User.Role.ADMIN, User.Role.MANAGER, User.Role.FINANCE}


def _can_manage_finance(user):
    return user.is_superuser or user.role in _CAN_MANAGE_FINANCE_ROLES


def _millions(value):
    return f"{float(value) / 1_000_000:.1f}"


def _finance_home_url(tab=None):
    url = reverse("finance:home")
    return f"{url}?tab={tab}" if tab else url


def _to_uzs(amount, currency, rate):
    return amount * rate if currency == Currency.USD else amount


def _convert_currency(amount, from_currency, to_currency, rate):
    """Convert between the two currencies the app supports. Returns None when a
    conversion is required but no usable rate is available, so callers can
    refuse the operation rather than silently booking a wrong figure."""
    if from_currency == to_currency:
        return amount
    if not rate or rate <= 0:
        return None
    if from_currency == Currency.USD and to_currency == Currency.UZS:
        return amount * rate
    if from_currency == Currency.UZS and to_currency == Currency.USD:
        return amount / rate
    return None


def _valid_uuid(value):
    """Filter ids arrive straight from the query string; a malformed one would
    raise ValidationError deep inside the queryset. Treat it as 'no filter'."""
    if not value:
        return None
    try:
        uuid.UUID(str(value))
    except (ValueError, AttributeError, TypeError):
        return None
    return value


def _parse_iso_date(value):
    """'2026-08-23' -> date, anything unparseable -> None (treated as 'no bound')."""
    if not value:
        return None
    try:
        return datetime.date.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _bucket_series(rows, date_from, date_to, rate):
    """Income/expense totals per time bucket, derived from the records that are
    already on screen. Buckets are days for short spans and months for long ones,
    so the chart stays readable without inventing any data points."""
    dates = [r.date for r in rows if r.date]
    if not dates:
        return {"points": [], "granularity": "day"}

    start = date_from or min(dates)
    end = date_to or max(dates)
    if start > end:
        start, end = end, start

    by_month = (end - start).days > 62
    buckets = {}

    def key_for(d):
        return d.replace(day=1) if by_month else d

    cur = key_for(start)
    while cur <= end:
        buckets[cur] = {"income": 0.0, "expense": 0.0}
        if by_month:
            cur = datetime.date(cur.year + 1, 1, 1) if cur.month == 12 else datetime.date(cur.year, cur.month + 1, 1)
        else:
            cur += datetime.timedelta(days=1)

    for r in rows:
        if not r.date:
            continue
        bucket = buckets.get(key_for(r.date))
        if bucket is None:
            continue
        value = _to_uzs(r.amount, r.currency, rate)
        if r.type == RecordType.INCOME:
            bucket["income"] += value
        else:
            bucket["expense"] += value

    label_fmt = "%m.%Y" if by_month else "%d.%m"
    points = [
        {"label": key.strftime(label_fmt), "income": data["income"], "expense": data["expense"]}
        for key, data in sorted(buckets.items())
    ]
    return {"points": points, "granularity": "month" if by_month else "day"}


def _account_sparkline(rows, account):
    """Running balance of one account over its own records, oldest to newest,
    in that account's own currency. Returns [] when there is nothing real to draw."""
    account_rows = sorted(
        [r for r in rows if r.account == account and r.date], key=lambda r: r.date
    )
    if len(account_rows) < 2:
        return []
    running = 0.0
    series = []
    for r in account_rows:
        running += r.signed_amount
        series.append(round(running, 2))
    return series[-24:]


def _get_month_nav(month_str=None):
    today = timezone.localdate()
    if month_str:
        try:
            year, mon = (int(part) for part in month_str.split("-", 1))
            cur = datetime.date(year, mon, 1)
        except (ValueError, TypeError):
            cur = datetime.date(today.year, today.month, 1)
    else:
        cur = datetime.date(today.year, today.month, 1)

    prev_date = (cur - datetime.timedelta(days=1)).replace(day=1)
    if cur.month == 12:
        next_date = datetime.date(cur.year + 1, 1, 1)
    else:
        next_date = datetime.date(cur.year, cur.month + 1, 1)

    return {
        "current": cur.strftime("%Y-%m"),
        "display": cur.strftime("%Y-%m"),
        "prev": prev_date.strftime("%Y-%m"),
        "next": next_date.strftime("%Y-%m"),
        "is_current": (cur.year == today.year and cur.month == today.month),
    }



def _dashboard_context(request):
    user = request.user
    projects = visible_projects_for(user)
    settings_obj = FinanceSettings.get_solo()
    rate = settings_obj.usd_rate

    all_records = FinancialRecord.objects.filter(project__in=projects, status=RecordStatus.CONFIRMED)

    # Optional period filter. With no ?from/?to given nothing is narrowed, so the
    # figures stay identical to the all-time totals this page has always shown.
    date_from = _parse_iso_date(request.GET.get("from"))
    date_to = _parse_iso_date(request.GET.get("to"))
    records = all_records
    admin_expenses_qs = AdministrativeExpense.objects.all()
    if date_from:
        records = records.filter(date__gte=date_from)
        admin_expenses_qs = admin_expenses_qs.filter(date__gte=date_from)
    if date_to:
        records = records.filter(date__lte=date_to)
        admin_expenses_qs = admin_expenses_qs.filter(date__lte=date_to)

    # Account cards are balances, not flows — they stay all-time on purpose so a
    # period filter never makes a bank balance look like it changed.
    all_records_list = list(all_records)
    account_balances = []
    for account, label in Account.choices:
        total = sum(r.signed_amount for r in all_records_list if r.account == account)
        sparkline = _account_sparkline(all_records_list, account)
        currency = ACCOUNT_CURRENCY[account]
        account_balances.append({
            "account": account, "label": label, "total": total,
            "currency": currency,
            "total_in_uzs": _to_uzs(total, currency, rate),
            "sparkline": sparkline,
            "sparkline_json": json.dumps(sparkline),
        })

    total_income = sum(
        _to_uzs(r.amount, r.currency, rate) for r in records.filter(type=RecordType.INCOME)
    )
    total_expense = sum(
        _to_uzs(r.amount, r.currency, rate)
        for r in records.filter(type__in=[RecordType.EXPENSE, RecordType.ADVANCE, RecordType.PAYMENT])
    )
    total_admin_expense = sum(
        _to_uzs(e.amount, e.currency, rate) for e in admin_expenses_qs
    )
    total_expense += total_admin_expense
    net_profit = total_income - total_expense

    contracts = EmployeeContract.objects.filter(project__in=projects)
    total_contract_amount = sum(_to_uzs(c.amount, c.currency, rate) for c in contracts)
    total_contract_paid = sum(_to_uzs(c.paid, c.currency, rate) for c in contracts)

    chart = _bucket_series(list(records), date_from, date_to, rate)

    project_rows = []
    for project in projects:
        project_records = records.filter(project=project)
        income_actual = sum(
            _to_uzs(r.amount, r.currency, rate) for r in project_records.filter(type=RecordType.INCOME)
        )
        expense_actual = sum(
            _to_uzs(r.amount, r.currency, rate)
            for r in project_records.filter(type__in=[RecordType.EXPENSE, RecordType.ADVANCE, RecordType.PAYMENT])
        )
        budget_uzs = _to_uzs(project.budget, project.currency, rate)
        income_expected = max(0, budget_uzs - income_actual)
        expense_expected = sum(
            _to_uzs(c.balance, c.currency, rate) for c in contracts.filter(project=project)
        )
        profit = (income_actual + income_expected) - (expense_actual + expense_expected)
        project_rows.append({
            "project": project,
            "budget": budget_uzs,
            "income_actual": income_actual,
            "expense_actual": expense_actual,
            "income_expected": income_expected,
            "expense_expected": expense_expected,
            "profit": profit,
        })

    project_totals = {
        "budget": sum(row["budget"] for row in project_rows),
        "income_actual": sum(row["income_actual"] for row in project_rows),
        "expense_actual": sum(row["expense_actual"] for row in project_rows),
        "income_expected": sum(row["income_expected"] for row in project_rows),
        "expense_expected": sum(row["expense_expected"] for row in project_rows),
        "profit": sum(row["profit"] for row in project_rows),
    }

    contract_paid_pct = round(total_contract_paid / total_contract_amount * 100) if total_contract_amount else 0

    # What the USD side of the balance sheet is worth at the current rate — the
    # rate card's own numbers, so it explains why the rate matters here.
    usd_holdings = sum(
        row["total"] for row in account_balances if row["currency"] == Currency.USD
    )
    uzs_holdings = sum(
        row["total"] for row in account_balances if row["currency"] == Currency.UZS
    )
    usd_holdings_in_uzs = usd_holdings * rate

    return {
        "account_balances": account_balances,
        "usd_rate": rate,
        "usd_rate_updated_at": settings_obj.updated_at,
        "net_profit": net_profit,
        "total_income": total_income,
        "total_expense": total_expense,
        "total_contract_amount": total_contract_amount,
        "total_budget": total_contract_amount,
        "total_contract_paid": total_contract_paid,
        "contract_paid_pct": contract_paid_pct,
        "usd_holdings": usd_holdings,
        "uzs_holdings": uzs_holdings,
        "usd_holdings_in_uzs": usd_holdings_in_uzs,
        "total_holdings_in_uzs": uzs_holdings + usd_holdings_in_uzs,
        "project_rows": project_rows,
        "project_totals": project_totals,
        "chart_points": chart["points"],
        "chart_granularity": chart["granularity"],
        "filter_from": request.GET.get("from") or "",
        "filter_to": request.GET.get("to") or "",
        "has_period_filter": bool(date_from or date_to),
        "transaction_form": TransactionForm(user=user),
        "employee_form": EmployeeContractForm(),
        "category_form": FinanceCategoryForm(),
        "can_manage_finance": _can_manage_finance(user),
    }


#: Donut palette, reused by the payroll fund-structure chart.
_PAYROLL_SLICE_COLORS = ["#5b9ee0", "#4ec99a", "#a78bfa", "#d9a441", "#e8796f", "#6ac9c0", "#c084c8"]


def _payroll_series(contracts, date_from, date_to, rate):
    """Cumulative accrued / paid / outstanding per bucket, built from the same
    contracts the KPIs and the table use, so every number on the page ties out.

    Both figures are attributed to the contract's creation date: a payment is
    recorded on EmployeeContract.paid, which keeps no per-payment history, and
    the salary/advance FinancialRecords it writes carry no FK back to the
    contract. Attributing to the accrual date is therefore the only grouping
    whose running totals end exactly at the fund and paid KPIs.
    """
    stamps = [c.created_at.date() for c in contracts]
    if not stamps:
        return {"points": [], "granularity": "day"}

    start = date_from or min(stamps)
    end = date_to or max(stamps)
    if start > end:
        start, end = end, start

    by_month = (end - start).days > 62

    def key_for(d):
        return d.replace(day=1) if by_month else d

    buckets = {}
    cur = key_for(start)
    while cur <= end:
        buckets[cur] = {"accrued": 0.0, "paid": 0.0}
        if by_month:
            cur = datetime.date(cur.year + 1, 1, 1) if cur.month == 12 else datetime.date(cur.year, cur.month + 1, 1)
        else:
            cur += datetime.timedelta(days=1)

    for c in contracts:
        bucket = buckets.get(key_for(c.created_at.date()))
        if bucket is None:
            continue
        bucket["accrued"] += _to_uzs(c.amount, c.currency, rate)
        bucket["paid"] += _to_uzs(c.paid, c.currency, rate)

    label_fmt = "%m.%Y" if by_month else "%d.%m"
    points = []
    run_accrued = run_paid = 0.0
    for key in sorted(buckets):
        run_accrued += buckets[key]["accrued"]
        run_paid += buckets[key]["paid"]
        points.append({
            "label": key.strftime(label_fmt),
            "accrued": run_accrued,
            "paid": run_paid,
            "remaining": max(0.0, run_accrued - run_paid),
        })
    return {"points": points, "granularity": "month" if by_month else "day"}


def _payroll_structure(contracts, rate):
    """Salary fund split by the employee's department — the existing field that
    actually records what kind of work the salary is for. Employees with no
    department fall into one 'Other' slice rather than inventing a category."""
    totals = {}
    for c in contracts:
        key = (c.user.department or "").strip() or str(_("Other"))
        totals[key] = totals.get(key, 0.0) + _to_uzs(c.amount, c.currency, rate)

    total = sum(totals.values())
    if not total:
        return []
    rows = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    return [
        {
            "label": name,
            "amount": value,
            "pct": round(value / total * 100, 1),
            "color": _PAYROLL_SLICE_COLORS[i % len(_PAYROLL_SLICE_COLORS)],
        }
        for i, (name, value) in enumerate(rows)
    ]


def _payroll_context(request):
    user = request.user
    projects = visible_projects_for(user)
    contracts = EmployeeContract.objects.filter(project__in=projects).select_related(
        "user", "project", "sub_object", "pod_object"
    )

    employee_id = _valid_uuid(request.GET.get("employee"))
    project_id = _valid_uuid(request.GET.get("project"))
    sub_object_id = _valid_uuid(request.GET.get("sub_object"))
    pod_object_id = _valid_uuid(request.GET.get("pod_object"))
    date_from = _parse_iso_date(request.GET.get("from"))
    date_to = _parse_iso_date(request.GET.get("to"))
    if employee_id:
        contracts = contracts.filter(user_id=employee_id)
    if project_id:
        contracts = contracts.filter(project_id=project_id)
    if sub_object_id:
        contracts = contracts.filter(sub_object_id=sub_object_id)
    if pod_object_id:
        contracts = contracts.filter(pod_object_id=pod_object_id)
    if date_from:
        contracts = contracts.filter(created_at__date__gte=date_from)
    if date_to:
        contracts = contracts.filter(created_at__date__lte=date_to)

    employees = User.objects.filter(employee_contracts__project__in=projects).distinct()

    # Everything below — KPIs, chart, donut, table — is derived from this one
    # filtered list, so the whole page always describes the same dataset.
    contract_list = list(contracts)
    settings_obj = FinanceSettings.get_solo()
    rate = settings_obj.usd_rate

    # Live balances for the "Give salary" modal. Keyed by contract id and taken
    # from the same objects the pay form offers, so what the dialog shows is
    # what the server will check against.
    pay_contracts = {
        str(c.pk): {
            "balance": round(c.balance, 2),
            "amount": round(c.amount, 2),
            "paid": round(c.paid, 2),
            "currency": c.currency,
            "employee": c.user.get_short_name(),
            "project": c.project.name,
        }
        for c in EmployeeContract.objects.filter(project__in=projects)
        .select_related("user", "project")
        .exclude(status__in=["completed", "terminated"])
        if c.balance > 0
    }

    fund_total = sum(_to_uzs(c.amount, c.currency, rate) for c in contract_list)
    paid_total = sum(_to_uzs(c.paid, c.currency, rate) for c in contract_list)
    remaining_total = fund_total - paid_total
    employee_count = len({c.user_id for c in contract_list})
    completion_pct = round(paid_total / fund_total * 100) if fund_total else 0

    series = _payroll_series(contract_list, date_from, date_to, rate)

    rows = []
    for c in contract_list:
        pct = round(c.paid / c.amount * 100) if c.amount else 0
        if c.balance <= 0 and c.amount:
            state = "paid"
        elif c.paid > 0:
            state = "partial"
        else:
            state = "unpaid"
        rows.append({"contract": c, "paid_pct": min(100, max(0, pct)), "state": state})

    return {
        "employee_contracts": contracts,
        "payroll_rows": rows,
        "payroll_fund": fund_total,
        "payroll_paid": paid_total,
        "payroll_remaining": remaining_total,
        "payroll_employee_count": employee_count,
        "payroll_completion_pct": completion_pct,
        "payroll_points": series["points"],
        "payroll_granularity": series["granularity"],
        "payroll_structure": _payroll_structure(contract_list, rate),
        "employee_form": EmployeeContractForm(),
        "pay_form": EmployeeContractPayForm(),
        "category_form": FinanceCategoryForm(),
        "transaction_form": TransactionForm(user=user),
        "pay_contracts": pay_contracts,
        "pay_meta": {"rate": rate or 0},
        "usd_rate": rate,
        "usd_rate_updated_at": settings_obj.updated_at,
        "can_manage_finance": _can_manage_finance(user),
        "account_currencies": {a: ACCOUNT_CURRENCY[a] for a, _l in Account.choices},
        "employees": employees,
        "projects": projects,
        "objects": SubObject.objects.filter(project__in=projects, parent__isnull=True),
        "pod_objects": SubObject.objects.filter(project__in=projects, parent__isnull=False),
        "filter_employee": employee_id or "",
        "filter_project": project_id or "",
        "filter_sub_object": sub_object_id or "",
        "filter_pod_object": pod_object_id or "",
        "filter_from": request.GET.get("from") or "",
        "filter_to": request.GET.get("to") or "",
        "has_payroll_filter": bool(
            employee_id or project_id or sub_object_id or pod_object_id or date_from or date_to
        ),
    }


def _filtered_cash_flow_records(request, projects):
    records = FinancialRecord.objects.filter(project__in=projects).select_related(
        "project", "sub_object"
    ).order_by("-date", "-created_at")
    project_id = _valid_uuid(request.GET.get("project"))
    sub_object_id = _valid_uuid(request.GET.get("sub_object"))
    pod_object_id = _valid_uuid(request.GET.get("pod_object"))
    month = request.GET.get("month")
    category = request.GET.get("category")
    if project_id:
        records = records.filter(project_id=project_id)
    if pod_object_id:
        records = records.filter(sub_object_id=pod_object_id)
    elif sub_object_id:
        records = records.filter(Q(sub_object_id=sub_object_id) | Q(sub_object__parent_id=sub_object_id))
    if month:
        try:
            year, mon = (int(part) for part in month.split("-", 1))
            records = records.filter(date__year=year, date__month=mon)
        except ValueError:
            pass
    if category:
        records = records.filter(category=category)
    return records


def _cash_flow_context(request):
    projects = visible_projects_for(request.user)
    records = _filtered_cash_flow_records(request, projects)
    totals = {c: 0 for c, _label in Currency.choices}
    for r in records:
        totals[r.currency] = totals.get(r.currency, 0) + r.signed_amount

    cat_choices = [(c.value, c.label) for c in RecordCategory]
    for fc in FinanceCategory.objects.all():
        cat_choices.append((fc.name, fc.name))

    month_str = request.GET.get("month") or ""

    return {
        "cash_flow_records": records[:300],
        "cash_flow_totals": totals,
        "projects": projects,
        "objects": SubObject.objects.filter(project__in=projects, parent__isnull=True),
        "pod_objects": SubObject.objects.filter(project__in=projects, parent__isnull=False),
        "categories": cat_choices,
        "filter_project": request.GET.get("project") or "",
        "filter_sub_object": request.GET.get("sub_object") or "",
        "filter_pod_object": request.GET.get("pod_object") or "",
        "filter_month": month_str,
        "filter_category": request.GET.get("category") or "",
        "month_nav": _get_month_nav(month_str),
        "category_form": FinanceCategoryForm(),
        "transaction_form": TransactionForm(user=request.user),
    }


def _admin_expenses_context(request):
    expenses = AdministrativeExpense.objects.select_related("created_by").order_by("-date", "-created_at")
    period = request.GET.get("period")
    category = request.GET.get("category")
    if period:
        expenses = expenses.filter(period=period)
    if category:
        expenses = expenses.filter(category=category)

    settings_obj = FinanceSettings.get_solo()
    rate = settings_obj.usd_rate
    totals = {c: 0 for c, _label in Currency.choices}
    for e in expenses:
        totals[e.currency] = totals.get(e.currency, 0) + e.amount
    total_uzs = sum(_to_uzs(e.amount, e.currency, rate) for e in expenses)

    admin_cats = [(c.value, c.label) for c in AdminExpenseCategory]
    for fc in FinanceCategory.objects.filter(type="admin"):
        admin_cats.append((fc.name, fc.name))

    return {
        "admin_expenses": expenses,
        "admin_expense_totals": totals,
        "admin_expense_total_uzs": total_uzs,
        "admin_expense_form": AdministrativeExpenseForm(),
        "admin_expense_categories": admin_cats,
        "category_form": FinanceCategoryForm(),
        "filter_period": period or "",
        "filter_admin_category": category or "",
        "can_manage_finance": _can_manage_finance(request.user),
    }



@login_required
def finance_home(request):
    tab = request.GET.get("tab", "dashboard")
    context = {"tab": tab, "can_manage_finance": _can_manage_finance(request.user)}
    if tab == "payroll":
        context.update(_payroll_context(request))
    elif tab == "cash_flow":
        context.update(_cash_flow_context(request))
    elif tab == "admin_expenses":
        # Ma'muriy xarajatlar butun tashkilot bo'yicha, hech qanday loyihaga
        # bog'lanmagan — ya'ni visible_projects_for() ularni cheklay olmaydi.
        # Shuning uchun bu bo'limni faqat moliyaviy rollar ko'radi.
        if not _can_manage_finance(request.user):
            raise PermissionDenied
        context.update(_admin_expenses_context(request))
    else:
        tab = context["tab"] = "dashboard"
        context.update(_dashboard_context(request))
    return render(request, "finance/finance_home.html", context)


@login_required
def transaction_create(request):
    if request.method == "POST":
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            project = form.cleaned_data["project"]
            if not can_edit_project(request.user, project):
                raise PermissionDenied
            record = form.save(commit=False)
            record.currency = ACCOUNT_CURRENCY[record.account]
            record.status = RecordStatus.CONFIRMED
            record.created_by = request.user
            record.save()
            messages.success(request, _("Transaction added."))
        else:
            messages.error(request, _("Could not add the transaction — please check the form."))
    return redirect(_finance_home_url("dashboard"))


@login_required
def update_exchange_rate(request):
    if not _can_manage_finance(request.user):
        raise PermissionDenied
    if request.method == "POST":
        rate = fetch_usd_rate()
        if rate and rate > 0:
            settings_obj = FinanceSettings.get_solo()
            settings_obj.usd_rate = rate
            settings_obj.updated_by = request.user
            settings_obj.save()
            messages.success(request, _("Exchange rate updated from the Central Bank of Uzbekistan."))
        else:
            messages.error(request, _("Could not fetch the exchange rate — please try again later."))
    return redirect(_finance_home_url("dashboard"))


@login_required
def update_exchange_rate_poytaxtbank(request):
    if not _can_manage_finance(request.user):
        raise PermissionDenied
    if request.method == "POST":
        rate = fetch_usd_rate_poytaxtbank()
        if rate and rate > 0:
            settings_obj = FinanceSettings.get_solo()
            settings_obj.usd_rate = rate
            settings_obj.updated_by = request.user
            settings_obj.save()
            messages.success(request, _("Exchange rate updated from Poytaxt Bank."))
        else:
            messages.error(request, _("Could not fetch the exchange rate — please try again later."))
    return redirect(_finance_home_url("dashboard"))


@login_required
def finance_record_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = FinancialRecordForm(request.POST)
        if form.is_valid():
            record = form.save(commit=False)
            record.project = project
            record.created_by = request.user
            record.save()
            messages.success(request, _("Finance record added."))
    return redirect("projects:detail", pk=project_pk)


@login_required
def finance_record_delete(request, pk):
    record = get_object_or_404(FinancialRecord, pk=pk)
    if not can_edit_project(request.user, record.project):
        raise PermissionDenied
    if request.method == "POST":
        project_pk = record.project_id
        record.delete()
        messages.success(request, _("Record deleted."))
        return redirect("projects:detail", pk=project_pk)
    return render(request, "finance/record_confirm_delete.html", {"record": record})


@login_required
def employee_contract_create(request):
    if request.method == "POST":
        form = EmployeeContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            if not can_edit_project(request.user, contract.project):
                raise PermissionDenied
            contract.save()
            messages.success(request, _("Employee contract added."))
        else:
            messages.error(request, _("Could not add the employee contract — please check the form."))
    return redirect(_finance_home_url("payroll"))


@login_required
def employee_contract_delete(request, pk):
    contract = get_object_or_404(EmployeeContract, pk=pk)
    if not can_edit_project(request.user, contract.project):
        raise PermissionDenied
    if request.method == "POST":
        contract.delete()
        messages.success(request, _("Employee contract deleted."))
    return redirect(_finance_home_url("payroll"))


@login_required
def employee_contract_pay(request):
    if request.method != "POST":
        return redirect(_finance_home_url("payroll"))

    form = EmployeeContractPayForm(request.POST)
    if not form.is_valid():
        messages.error(request, _("Could not record the payment — please check the form."))
        return redirect(_finance_home_url("payroll"))

    contract = form.cleaned_data["employee_contract"]
    if not can_edit_project(request.user, contract.project):
        raise PermissionDenied

    amount = form.cleaned_data["amount"]
    pay_currency = form.cleaned_data["payment_currency"]
    account = form.cleaned_data["account"]
    rate = FinanceSettings.get_solo().usd_rate

    # The money can leave in a different currency than the contract is written
    # in; the balance must always move by the contract-currency equivalent.
    if pay_currency != contract.currency and not rate:
        messages.error(request, _("Could not fetch the exchange rate — please try again later."))
        return redirect(_finance_home_url("payroll"))

    applied = _convert_currency(amount, pay_currency, contract.currency, rate)
    if applied is None:
        messages.error(request, _("Could not fetch the exchange rate — please try again later."))
        return redirect(_finance_home_url("payroll"))
    if contract.currency == Currency.UZS:
        applied = round(applied)          # balances are whole som
    if applied <= 0:
        messages.error(request, _("Could not record the payment — please check the form."))
        return redirect(_finance_home_url("payroll"))

    record_type = RecordType.ADVANCE if form.cleaned_data["is_advance"] else RecordType.PAYMENT
    description = (form.cleaned_data.get("description") or "").strip() or (
        _("Salary payment — %(employee)s") % {"employee": contract.user.get_short_name()}
    )

    # Lock the row so a concurrent payment cannot read a stale balance and
    # overshoot it: the check and the increment happen under the same lock.
    with transaction.atomic():
        locked = EmployeeContract.objects.select_for_update().get(pk=contract.pk)
        if applied > locked.balance + 1e-6:
            messages.error(request, _("The payment amount exceeds the remaining balance."))
            return redirect(_finance_home_url("payroll"))

        FinancialRecord.objects.create(
            project=locked.project, sub_object=locked.sub_object or locked.pod_object,
            type=record_type, account=account, amount=amount, currency=pay_currency,
            exchange_rate=rate if pay_currency != locked.currency else None,
            description=description,
            date=timezone.localdate(), status=RecordStatus.CONFIRMED, created_by=request.user,
        )
        locked.paid = F("paid") + applied
        locked.save(update_fields=["paid", "updated_at"])

    messages.success(request, _("Payment recorded."))
    return redirect(_finance_home_url("payroll"))


@login_required
def administrative_expense_create(request):
    if not _can_manage_finance(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = AdministrativeExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.created_by = request.user
            expense.save()
            messages.success(request, _("Administrative expense added."))
        else:
            messages.error(request, _("Could not add the expense — please check the form."))
    return redirect(_finance_home_url("admin_expenses"))


@login_required
def administrative_expense_delete(request, pk):
    if not _can_manage_finance(request.user):
        raise PermissionDenied
    expense = get_object_or_404(AdministrativeExpense, pk=pk)
    if request.method == "POST":
        expense.delete()
        messages.success(request, _("Administrative expense deleted."))
    return redirect(_finance_home_url("admin_expenses"))


@login_required
def cash_flow_export(request):
    projects = visible_projects_for(request.user)
    records = _filtered_cash_flow_records(request, projects)
    wb = build_cash_flow_workbook(records)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="cash_flow.xlsx"'
    wb.save(response)
    return response


@login_required
def finance_category_create(request):
    if not _can_manage_finance(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = FinanceCategoryForm(request.POST)
        if form.is_valid():
            cat = form.save(commit=False)
            cat.created_by = request.user
            cat.save()
            messages.success(request, _("Category added successfully."))
        else:
            messages.error(request, _("Could not add category — please check the form."))
    tab = request.POST.get("return_tab", "dashboard")
    return redirect(_finance_home_url(tab))

