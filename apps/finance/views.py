from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError
from django.db.models import Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.notifications.services import notify_user
from apps.projects.models import Project
from apps.projects.permissions import can_edit_project, ensure_project_member, visible_projects_for
from apps.tasks.models import Task

from .forms import (
    ContractForm,
    ContractorForm,
    CostCodeForm,
    EmployeeContractForm,
    FinancialRecordForm,
    PaymentApprovalReviewForm,
    PaymentRequestForm,
)
from .models import (
    MANAGER_APPROVAL_THRESHOLD,
    EmployeeContract,
    FinancialRecord,
    PaymentApprovalStage,
    PaymentApprovalStatus,
    PaymentRequest,
    PaymentStatus,
    RecordStatus,
    RecordType,
)

_APPROVAL_STAGE_DEFS = [
    (1, _("GIP approval"), User.Role.GIP),
    (2, _("Finance review"), User.Role.FINANCE),
    (3, _("Manager approval"), User.Role.MANAGER),
]


def _employees_tab_url():
    return f"{reverse('finance:home')}?tab=employees"


def _finance_home_url(project=None):
    url = reverse("finance:home")
    return f"{url}?project={project.pk}" if project else url


def _millions(value):
    return f"{float(value) / 1_000_000:.1f}"


def _selected_project(request, projects):
    project_id = request.GET.get("project")
    if project_id:
        match = projects.filter(pk=project_id).first()
        if match:
            return match
    return projects.first()


def _create_approval_chain(payment):
    for order, name, role in _APPROVAL_STAGE_DEFS:
        skip = order == 3 and payment.amount < MANAGER_APPROVAL_THRESHOLD
        stage = PaymentApprovalStage.objects.create(
            payment_request=payment, stage_order=order, stage_name=name, required_role=role,
            status=PaymentApprovalStatus.SKIPPED if skip else PaymentApprovalStatus.PENDING,
            comment=_("Automatic: amount under $%(threshold)s.") % {"threshold": MANAGER_APPROVAL_THRESHOLD}
            if skip else None,
            reviewed_at=timezone.now() if skip else None,
        )
        if not skip and order == 1:
            _notify_stage_reviewers(stage)


def _notify_stage_reviewers(stage):
    reviewers = User.objects.filter(role=stage.required_role, is_active=True)
    for reviewer in reviewers:
        ensure_project_member(stage.payment_request.project, reviewer)
        notify_user(
            reviewer, "finance", _("New payment request to review"),
            _("%(contractor)s — %(amount)s needs your approval.") % {
                "contractor": stage.payment_request.contractor, "amount": stage.payment_request.amount,
            },
            link=_finance_home_url(stage.payment_request.project),
        )


def _can_review_stage(user, stage):
    if user.is_superuser or user.role == User.Role.ADMIN:
        return stage.status == PaymentApprovalStatus.PENDING
    if user.role != stage.required_role or stage.status != PaymentApprovalStatus.PENDING:
        return False
    earlier = stage.payment_request.approval_stages.filter(stage_order__lt=stage.stage_order)
    return not earlier.exclude(
        status__in=[PaymentApprovalStatus.APPROVED, PaymentApprovalStatus.SKIPPED]
    ).exists()


def _project_overview(project, user):
    today = timezone.localdate()

    income_pending = FinancialRecord.objects.filter(
        project=project, type=RecordType.INCOME, status=RecordStatus.PENDING
    )
    receivable_total = income_pending.aggregate(total=Sum("amount"))["total"] or 0
    receivable_overdue = income_pending.filter(date__lt=today).count()

    payables = PaymentRequest.objects.filter(project=project).exclude(status=PaymentStatus.REJECTED)
    payable_gross = payables.aggregate(total=Sum("amount"))["total"] or 0
    retainage_total = payables.aggregate(total=Sum("retainage_amount"))["total"] or 0

    confirmed = FinancialRecord.objects.filter(project=project, status=RecordStatus.CONFIRMED)
    received = confirmed.filter(type=RecordType.INCOME).aggregate(total=Sum("amount"))["total"] or 0
    expenses = confirmed.filter(type=RecordType.EXPENSE).aggregate(total=Sum("amount"))["total"] or 0
    margin = received - expenses
    margin_pct = round(margin / received * 100, 1) if received else 0

    tasks = Task.objects.filter(project=project)
    task_count = tasks.count()
    done_count = tasks.filter(status__in=[Task.Status.COMPLETED, Task.Status.APPROVED]).count()
    percent_complete = (done_count / task_count) if task_count else 0
    earned_value = percent_complete * project.budget
    actual_cost = PaymentRequest.objects.filter(
        project=project, status=PaymentStatus.APPROVED
    ).aggregate(total=Sum("amount"))["total"] or 0

    planned_value = None
    if project.start_date and project.deadline and project.deadline > project.start_date:
        elapsed_days = (today - project.start_date).days
        total_days = (project.deadline - project.start_date).days
        time_fraction = max(0, min(1, elapsed_days / total_days))
        planned_value = time_fraction * project.budget

    cpi = round(earned_value / actual_cost, 2) if actual_cost else None
    spi = round(earned_value / planned_value, 2) if planned_value else None

    cost_code_rows = []
    for cost_code in project.cost_codes.annotate(
        actual=Sum("payment_requests__amount", filter=Q(payment_requests__status=PaymentStatus.APPROVED))
    ):
        actual = cost_code.actual or 0
        diff = cost_code.budget - actual
        diff_pct = (diff / cost_code.budget) if cost_code.budget else 0
        if diff_pct > 0.05:
            status_variant, status_label = "success", _("Under budget")
        elif diff_pct < -0.02:
            status_variant, status_label = "danger", _("Over budget")
        else:
            status_variant, status_label = "default", _("On track")
        cost_code_rows.append({
            "cost_code": cost_code,
            "actual": actual,
            "diff": diff,
            "percent": min(100, round(actual / cost_code.budget * 100)) if cost_code.budget else 0,
            "status_variant": status_variant,
            "status_label": status_label,
        })

    months = []
    cursor = today.replace(day=1)
    for _month_index in range(6):
        months.append(cursor)
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    months.reverse()

    cash_rows = (
        FinancialRecord.objects.filter(
            project=project, status=RecordStatus.CONFIRMED, date__gte=months[0],
            type__in=[RecordType.INCOME, RecordType.EXPENSE],
        )
        .annotate(month=TruncMonth("date"))
        .values("month", "type")
        .annotate(total=Sum("amount"))
    )
    cash_flow_map = {}
    for row in cash_rows:
        key = row["month"].strftime("%Y-%m")
        bucket = cash_flow_map.setdefault(key, {"income": 0, "expense": 0})
        bucket["income" if row["type"] == RecordType.INCOME else "expense"] = row["total"]

    cash_flow = [
        {
            "label": month.strftime("%b"),
            "income": cash_flow_map.get(month.strftime("%Y-%m"), {}).get("income", 0),
            "expense": cash_flow_map.get(month.strftime("%Y-%m"), {}).get("expense", 0),
        }
        for month in months
    ]
    cash_flow_max = max([max(c["income"], c["expense"]) for c in cash_flow] + [1])

    payment_requests = (
        PaymentRequest.objects.filter(project=project)
        .select_related("contractor", "cost_code")
        .prefetch_related("approval_stages")[:50]
    )
    payment_rows = []
    for payment in payment_requests:
        stages = list(payment.approval_stages.all())
        next_stage = next((s for s in stages if s.status == PaymentApprovalStatus.PENDING), None)
        payment_rows.append({
            "payment": payment,
            "stages": stages,
            "next_stage": next_stage,
            "can_review": bool(next_stage) and _can_review_stage(user, next_stage),
        })

    return {
        "receivable_total": receivable_total,
        "receivable_overdue": receivable_overdue,
        "payable_net": payable_gross - retainage_total,
        "retainage_total": retainage_total,
        "margin": margin,
        "margin_pct": margin_pct,
        "cpi": cpi,
        "spi": spi,
        "cost_code_rows": cost_code_rows,
        "cash_flow": cash_flow,
        "cash_flow_max": cash_flow_max,
        "cash_flow_json": {"months": cash_flow, "max": cash_flow_max},
        "payment_rows": payment_rows,
        "payment_request_form": PaymentRequestForm(project=project),
        "cost_code_form": CostCodeForm(),
        "contractor_form": ContractorForm(),
        "manager_threshold": MANAGER_APPROVAL_THRESHOLD,
    }


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
        project = _selected_project(request, projects)
        confirmed = records.filter(status=RecordStatus.CONFIRMED)
        context.update({
            "selected_project": project,
            "total_budget": sum(p.budget for p in projects),
            "total_paid": sum(p.paid_amount for p in projects),
            "received": sum(r.amount for r in confirmed.filter(type=RecordType.INCOME)),
            "expenses": sum(r.amount for r in confirmed.filter(type=RecordType.EXPENSE)),
            "pending": sum(r.amount for r in records.filter(status=RecordStatus.PENDING)),
        })
        if project:
            context["can_edit"] = can_edit_project(request.user, project)
            context.update(_project_overview(project, request.user))

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


@login_required
def cost_code_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = CostCodeForm(request.POST)
        if form.is_valid():
            cost_code = form.save(commit=False)
            cost_code.project = project
            try:
                cost_code.save()
                messages.success(request, _("Cost code added."))
            except IntegrityError:
                messages.error(request, _("This cost code already exists for this project."))
        else:
            messages.error(request, _("Could not add the cost code — please check the form."))
    return redirect(_finance_home_url(project))


@login_required
def contractor_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = ContractorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, _("Contractor added."))
        else:
            messages.error(request, _("Could not add the contractor — please check the form."))
    return redirect(_finance_home_url(project))


@login_required
def payment_request_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = PaymentRequestForm(request.POST, request.FILES, project=project)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.project = project
            payment.requested_by = request.user
            payment.save()
            _create_approval_chain(payment)
            messages.success(request, _("Payment request submitted."))
        else:
            messages.error(request, _("Could not submit the payment request — please check the form."))
    return redirect(_finance_home_url(project))


@login_required
def payment_stage_review(request, stage_id):
    stage = get_object_or_404(PaymentApprovalStage, pk=stage_id)
    payment = stage.payment_request
    if payment.project not in visible_projects_for(request.user):
        raise PermissionDenied
    if not _can_review_stage(request.user, stage):
        raise PermissionDenied

    if request.method == "POST":
        form = PaymentApprovalReviewForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data["status"]
            stage.status = new_status
            stage.comment = form.cleaned_data.get("comment")
            stage.reviewer = request.user
            stage.reviewed_at = timezone.now()
            stage.save()

            if new_status == PaymentApprovalStatus.REJECTED:
                payment.status = PaymentStatus.REJECTED
                payment.save(update_fields=["status", "updated_at"])
                notify_user(
                    payment.requested_by, "finance", _("Payment request rejected"),
                    _("Your payment request for %(contractor)s was rejected.") % {
                        "contractor": payment.contractor},
                    link=_finance_home_url(payment.project),
                )
            else:
                remaining = payment.approval_stages.filter(
                    status=PaymentApprovalStatus.PENDING
                ).order_by("stage_order")
                if remaining.exists():
                    _notify_stage_reviewers(remaining.first())
                else:
                    payment.status = PaymentStatus.APPROVED
                    payment.save(update_fields=["status", "updated_at"])
                    notify_user(
                        payment.requested_by, "finance", _("Payment request approved"),
                        _("Your payment request for %(contractor)s was fully approved.") % {
                            "contractor": payment.contractor},
                        link=_finance_home_url(payment.project),
                    )
            messages.success(request, _("Review submitted."))
            return redirect(_finance_home_url(payment.project))
    else:
        form = PaymentApprovalReviewForm()
    return render(request, "finance/payment_stage_review.html", {
        "stage": stage, "payment": payment, "form": form,
    })
