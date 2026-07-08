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
    elif tab == "employees":
        context["employee_contracts"] = EmployeeContract.objects.filter(
            project__in=projects
        ).select_related("user", "project")
        context["employee_form"] = EmployeeContractForm()
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
