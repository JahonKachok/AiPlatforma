from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render

from apps.accounts.models import User
from apps.documents.models import Document, DocumentStatus
from apps.finance.models import EmployeeContract, FinancialRecord
from apps.projects.permissions import visible_projects_for
from apps.tasks.models import Task

from .exports import (
    build_employees_workbook,
    build_finance_workbook,
    build_projects_workbook,
    build_tasks_workbook,
)


@login_required
def reports_dashboard(request):
    projects = visible_projects_for(request.user)
    tasks = Task.objects.filter(project__in=projects)
    documents = Document.objects.filter(project__in=projects)
    records = FinancialRecord.objects.filter(project__in=projects)

    tasks_total = tasks.count()
    tasks_completed = tasks.filter(status=Task.Status.COMPLETED).count()
    docs_total = documents.count()
    docs_approved = documents.filter(status=DocumentStatus.APPROVED).count()
    total_paid = sum(p.paid_amount for p in projects)
    active_employees = EmployeeContract.objects.filter(project__in=projects, status="active").values("user").distinct().count()
    total_employees = EmployeeContract.objects.filter(project__in=projects).values("user").distinct().count()

    status_distribution = [
        {
            "label": label,
            "count": tasks.filter(status=value).count(),
            "pct": round(tasks.filter(status=value).count() / tasks_total * 100) if tasks_total else 0,
        }
        for value, label in Task.Status.choices
    ]
    project_status_distribution = [
        {"label": label, "count": projects.filter(status=value).count()}
        for value, label in projects.model.Status.choices
    ]
    workload = (
        User.objects.filter(assigned_tasks__project__in=projects)
        .annotate(task_count=Count("assigned_tasks"))
        .order_by("-task_count")[:10]
    )

    return render(request, "reports/dashboard.html", {
        "tasks_total": tasks_total, "tasks_completed": tasks_completed,
        "docs_total": docs_total, "docs_approved": docs_approved,
        "total_paid": total_paid,
        "active_employees": active_employees, "total_employees": total_employees,
        "status_distribution": status_distribution,
        "project_status_distribution": project_status_distribution,
        "workload": workload,
    })


@login_required
def report_export(request, kind):
    projects = visible_projects_for(request.user)

    if kind == "projects":
        wb = build_projects_workbook(projects)
    elif kind == "tasks":
        wb = build_tasks_workbook(Task.objects.filter(project__in=projects).select_related("project", "assignee"))
    elif kind == "finance":
        wb = build_finance_workbook(FinancialRecord.objects.filter(project__in=projects).select_related("project"))
    elif kind == "employees":
        rows_data = []
        for ec in EmployeeContract.objects.filter(project__in=projects).select_related("user"):
            user_tasks = Task.objects.filter(project__in=projects, assignee=ec.user)
            rows_data.append({
                "name": ec.user.full_name,
                "tasks_total": user_tasks.count(),
                "tasks_completed": user_tasks.filter(status=Task.Status.COMPLETED).count(),
                "contract_amount": ec.amount,
                "paid": ec.paid,
                "balance": ec.balance,
            })
        wb = build_employees_workbook(rows_data)
    else:
        return HttpResponseBadRequest("Unknown export kind")

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{kind}_report.xlsx"'
    wb.save(response)
    return response
