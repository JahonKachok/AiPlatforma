from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
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

from .forms import (
    EmployeeContractForm,
    EmployeeContractPayForm,
    FinancialRecordForm,
    TransactionForm,
)
from .models import (
    ACCOUNT_CURRENCY,
    Account,
    Currency,
    EmployeeContract,
    FinanceSettings,
    FinancialRecord,
    RecordStatus,
    RecordType,
)
from .services import fetch_usd_rate

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


def _dashboard_context(request):
    user = request.user
    projects = visible_projects_for(user)
    settings_obj = FinanceSettings.get_solo()
    rate = settings_obj.usd_rate

    records = FinancialRecord.objects.filter(project__in=projects, status=RecordStatus.CONFIRMED)

    account_balances = []
    for account, label in Account.choices:
        total = sum(r.signed_amount for r in records.filter(account=account))
        account_balances.append({
            "account": account, "label": label, "total": total, "currency": ACCOUNT_CURRENCY[account],
        })

    total_income = sum(
        _to_uzs(r.amount, r.currency, rate) for r in records.filter(type=RecordType.INCOME)
    )
    total_expense = sum(
        _to_uzs(r.amount, r.currency, rate)
        for r in records.filter(type__in=[RecordType.EXPENSE, RecordType.ADVANCE, RecordType.PAYMENT])
    )
    net_profit = total_income - total_expense

    contracts = EmployeeContract.objects.filter(project__in=projects)

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
            "income_actual": income_actual,
            "expense_actual": expense_actual,
            "income_expected": income_expected,
            "expense_expected": expense_expected,
            "profit": profit,
        })

    return {
        "account_balances": account_balances,
        "usd_rate": rate,
        "usd_rate_updated_at": settings_obj.updated_at,
        "net_profit": net_profit,
        "total_income": total_income,
        "total_expense": total_expense,
        "project_rows": project_rows,
        "transaction_form": TransactionForm(user=user),
        "can_manage_finance": _can_manage_finance(user),
    }


def _payroll_context(request):
    user = request.user
    projects = visible_projects_for(user)
    contracts = EmployeeContract.objects.filter(project__in=projects).select_related(
        "user", "project", "sub_object", "pod_object"
    )

    employee_id = request.GET.get("employee")
    project_id = request.GET.get("project")
    sub_object_id = request.GET.get("sub_object")
    pod_object_id = request.GET.get("pod_object")
    if employee_id:
        contracts = contracts.filter(user_id=employee_id)
    if project_id:
        contracts = contracts.filter(project_id=project_id)
    if sub_object_id:
        contracts = contracts.filter(sub_object_id=sub_object_id)
    if pod_object_id:
        contracts = contracts.filter(pod_object_id=pod_object_id)

    employees = User.objects.filter(employee_contracts__project__in=projects).distinct()

    return {
        "employee_contracts": contracts,
        "employee_form": EmployeeContractForm(),
        "pay_form": EmployeeContractPayForm(),
        "employees": employees,
        "projects": projects,
        "objects": SubObject.objects.filter(project__in=projects, parent__isnull=True),
        "pod_objects": SubObject.objects.filter(project__in=projects, parent__isnull=False),
        "filter_employee": employee_id or "",
        "filter_project": project_id or "",
        "filter_sub_object": sub_object_id or "",
        "filter_pod_object": pod_object_id or "",
    }


def _filtered_cash_flow_records(request, projects):
    records = FinancialRecord.objects.filter(project__in=projects).select_related("project", "sub_object")
    project_id = request.GET.get("project")
    sub_object_id = request.GET.get("sub_object")
    pod_object_id = request.GET.get("pod_object")
    if project_id:
        records = records.filter(project_id=project_id)
    if pod_object_id:
        records = records.filter(sub_object_id=pod_object_id)
    elif sub_object_id:
        records = records.filter(Q(sub_object_id=sub_object_id) | Q(sub_object__parent_id=sub_object_id))
    return records


def _cash_flow_context(request):
    projects = visible_projects_for(request.user)
    records = _filtered_cash_flow_records(request, projects)
    return {
        "cash_flow_records": records[:300],
        "projects": projects,
        "objects": SubObject.objects.filter(project__in=projects, parent__isnull=True),
        "pod_objects": SubObject.objects.filter(project__in=projects, parent__isnull=False),
        "filter_project": request.GET.get("project") or "",
        "filter_sub_object": request.GET.get("sub_object") or "",
        "filter_pod_object": request.GET.get("pod_object") or "",
    }


@login_required
def finance_home(request):
    tab = request.GET.get("tab", "dashboard")
    context = {"tab": tab}
    if tab == "payroll":
        context.update(_payroll_context(request))
    elif tab == "cash_flow":
        context.update(_cash_flow_context(request))
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
    if request.method == "POST":
        form = EmployeeContractPayForm(request.POST)
        if form.is_valid():
            contract = form.cleaned_data["employee_contract"]
            if not can_edit_project(request.user, contract.project):
                raise PermissionDenied
            amount = form.cleaned_data["amount"]
            if amount > contract.balance + 1e-6:
                messages.error(request, _("The payment amount exceeds the remaining balance."))
                return redirect(_finance_home_url("payroll"))

            account = form.cleaned_data["account"]
            record_type = RecordType.ADVANCE if form.cleaned_data["is_advance"] else RecordType.PAYMENT
            currency = ACCOUNT_CURRENCY[account]
            FinancialRecord.objects.create(
                project=contract.project, sub_object=contract.sub_object or contract.pod_object,
                type=record_type, account=account, amount=amount, currency=currency,
                description=_("Salary payment — %(employee)s") % {"employee": contract.user.get_short_name()},
                date=timezone.localdate(), status=RecordStatus.CONFIRMED, created_by=request.user,
            )
            contract.paid = F("paid") + amount
            contract.save(update_fields=["paid", "updated_at"])
            messages.success(request, _("Payment recorded."))
        else:
            messages.error(request, _("Could not record the payment — please check the form."))
    return redirect(_finance_home_url("payroll"))


@login_required
def cash_flow_export(request):
    projects = visible_projects_for(request.user)
    records = _filtered_cash_flow_records(request, projects)
    wb = build_cash_flow_workbook(records)
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="cash_flow.xlsx"'
    wb.save(response)
    return response
