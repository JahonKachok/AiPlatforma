from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.projects.models import Project
from apps.projects.permissions import can_edit_project, visible_projects_for

from .forms import ContractForm, EmployeeContractForm, FinancialRecordForm
from .models import EmployeeContract, FinancialRecord, RecordStatus, RecordType


def _employees_tab_url():
    return f"{reverse('finance:home')}?tab=employees"


def _millions(value):
    return f"{float(value) / 1_000_000:.1f}"


@login_required
def finance_home(request):
    tab = request.GET.get("tab", "overview")
    projects = visible_projects_for(request.user)
    records = FinancialRecord.objects.filter(project__in=projects)

    context = {"tab": tab, "projects": projects}

    if tab == "records":
        project_id = request.GET.get("project")
        if project_id:
            records = records.filter(project_id=project_id)
        context["records"] = records.select_related("project")[:200]
        context["project_id"] = project_id or ""
        confirmed = records.filter(status=RecordStatus.CONFIRMED)
        context["stat_cards"] = [
            {"label": _("Records"), "value": records.count()},
            {"label": _("Income"), "value": _millions(sum(
                r.amount for r in confirmed.filter(type=RecordType.INCOME))),
             "color": "text-green-600 dark:text-green-400", "sub": _("mln")},
            {"label": _("Expenses"), "value": _millions(sum(
                r.amount for r in confirmed.filter(type=RecordType.EXPENSE))),
             "color": "text-red-600 dark:text-red-400", "sub": _("mln")},
            {"label": _("Pending"), "value": _millions(sum(
                r.amount for r in records.filter(status=RecordStatus.PENDING))),
             "color": "text-amber-600 dark:text-amber-400", "sub": _("mln")},
        ]
    elif tab == "employees":
        contracts = EmployeeContract.objects.filter(
            project__in=projects
        ).select_related("user", "project")
        context["employee_contracts"] = contracts
        context["employee_form"] = EmployeeContractForm()
        total_amount = sum(c.amount for c in contracts)
        total_paid = sum(c.paid for c in contracts)
        context["stat_cards"] = [
            {"label": _("Contracts"), "value": contracts.count()},
            {"label": _("Contract amount"), "value": _millions(total_amount),
             "color": "text-blue-600 dark:text-blue-400", "sub": _("mln")},
            {"label": _("Paid"), "value": _millions(total_paid),
             "color": "text-green-600 dark:text-green-400", "sub": _("mln")},
            {"label": _("Balance"), "value": _millions(total_amount - total_paid),
             "color": "text-amber-600 dark:text-amber-400", "sub": _("mln")},
        ]
    else:
        confirmed = records.filter(status=RecordStatus.CONFIRMED)
        context.update({
            "total_budget": sum(p.budget for p in projects),
            "total_paid": sum(p.paid_amount for p in projects),
            "received": sum(r.amount for r in confirmed.filter(type=RecordType.INCOME)),
            "expenses": sum(r.amount for r in confirmed.filter(type=RecordType.EXPENSE)),
            "pending": sum(r.amount for r in records.filter(status=RecordStatus.PENDING)),
        })

    return render(request, "finance/finance_home.html", context)


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
def contract_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = ContractForm(request.POST, request.FILES)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.project = project
            contract.created_by = request.user
            contract.save()
            messages.success(request, _("Contract added."))
    return redirect("projects:detail", pk=project_pk)


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
    return redirect(_employees_tab_url())


@login_required
def employee_contract_delete(request, pk):
    contract = get_object_or_404(EmployeeContract, pk=pk)
    if not can_edit_project(request.user, contract.project):
        raise PermissionDenied
    if request.method == "POST":
        contract.delete()
        messages.success(request, _("Employee contract deleted."))
    return redirect(_employees_tab_url())
