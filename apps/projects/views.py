from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.documents.models import AuditLog
from apps.finance.forms import FinancialRecordForm
from apps.tasks.models import Task

from .forms import ProjectForm, ProjectMemberForm, SectionForm, SubObjectForm
from .models import Project, ProjectMember
from .permissions import can_create_project, can_edit_project, visible_projects_for

TRACKED_FIELDS = [
    "name", "description", "client_name", "client_contact", "address",
    "stage", "status", "start_date", "deadline", "budget", "paid_amount",
]


@login_required
def project_list(request):
    visible = visible_projects_for(request.user)
    projects = visible

    status = request.GET.get("status")
    if status:
        projects = projects.filter(status=status)
    search = request.GET.get("search")
    if search:
        projects = projects.filter(name__icontains=search)

    paginator = Paginator(projects, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    today = date.today()
    stat_cards = [
        {"label": _("Total"), "value": visible.count()},
        {"label": _("Active"), "value": visible.filter(status=Project.Status.ACTIVE).count(),
         "color": "text-blue-600 dark:text-blue-400"},
        {"label": _("Completed"), "value": visible.filter(status=Project.Status.COMPLETED).count(),
         "color": "text-green-600 dark:text-green-400"},
        {"label": _("Deadline passed"), "value": visible.filter(
            status=Project.Status.ACTIVE, deadline__lt=today).count(),
         "color": "text-red-600 dark:text-red-400"},
    ]

    return render(request, "projects/project_list.html", {
        "page_obj": page_obj,
        "status": status or "",
        "search": search or "",
        "statuses": Project.Status.choices,
        "can_create": can_create_project(request.user),
        "stat_cards": stat_cards,
    })


@login_required
def project_create(request):
    if not can_create_project(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            ProjectMember.objects.get_or_create(
                project=project, user=request.user, defaults={"role_in_project": "owner"}
            )
            gip = form.cleaned_data.get("gip")
            if gip:
                ProjectMember.objects.update_or_create(
                    project=project, user=gip, defaults={"role_in_project": "gip"}
                )
            AuditLog.log(obj=project, action="created", user=request.user)
            messages.success(request, _("Project created."))
            return redirect("projects:detail", pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, "projects/project_form.html", {"form": form, "is_create": True})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects.prefetch_related("members__user", "sub_objects", "sections"), pk=pk
    )
    if project not in visible_projects_for(request.user):
        raise PermissionDenied

    tasks = project.tasks.select_related("assignee")[:6]
    task_stats = {
        "total": project.tasks.count(),
        "completed": project.tasks.filter(status=Task.Status.COMPLETED).count(),
        "in_progress": project.tasks.filter(status=Task.Status.IN_PROGRESS).count(),
    }
    records = project.financial_records.all()[:20]
    income = sum(r.amount for r in project.financial_records.filter(type="income"))
    expense = sum(r.amount for r in project.financial_records.filter(type="expense"))

    return render(request, "projects/project_detail.html", {
        "project": project,
        "tasks": tasks,
        "task_stats": task_stats,
        "records": records,
        "income": income,
        "expense": expense,
        "can_edit": can_edit_project(request.user, project),
        "sub_object_form": SubObjectForm(),
        "section_form": SectionForm(project=project),
        "member_form": ProjectMemberForm(),
        "record_form": FinancialRecordForm(),
    })


@login_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied

    before = {f: getattr(project, f) for f in TRACKED_FIELDS}
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            after = {f: getattr(project, f) for f in TRACKED_FIELDS}
            changes = {f: [str(before[f]), str(after[f])] for f in TRACKED_FIELDS if before[f] != after[f]}
            if changes:
                AuditLog.log(obj=project, action="updated", user=request.user, details=changes)
            messages.success(request, _("Project updated."))
            return redirect("projects:detail", pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, "projects/project_form.html", {"form": form, "project": project, "is_create": False})


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        AuditLog.log(obj=project, action="deleted", user=request.user)
        project.delete()
        messages.success(request, _("Project deleted."))
        return redirect("projects:list")
    return render(request, "projects/project_confirm_delete.html", {"project": project})


@login_required
def project_history(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project not in visible_projects_for(request.user):
        raise PermissionDenied
    from django.contrib.contenttypes.models import ContentType
    entries = AuditLog.objects.filter(
        content_type=ContentType.objects.get_for_model(Project), object_id=str(project.pk)
    )[:200]
    return render(request, "projects/project_history.html", {"project": project, "entries": entries})


@login_required
def project_add_member(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = ProjectMemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.project = project
            if not ProjectMember.objects.filter(project=project, user=member.user).exists():
                member.save()
                messages.success(request, _("Member added."))
            else:
                messages.error(request, _("This user is already a member."))
    return redirect("projects:detail", pk=pk)


@login_required
def project_remove_member(request, pk, user_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    ProjectMember.objects.filter(project=project, user_id=user_id).delete()
    messages.success(request, _("Member removed."))
    return redirect("projects:detail", pk=pk)


@login_required
def project_add_subobject(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = SubObjectForm(request.POST)
        if form.is_valid():
            sub_object = form.save(commit=False)
            sub_object.project = project
            sub_object.save()
            messages.success(request, _("Sub-object added."))
    return redirect("projects:detail", pk=pk)


@login_required
def project_add_section(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = SectionForm(request.POST, project=project)
        if form.is_valid():
            section = form.save(commit=False)
            section.project = project
            section.save()
            messages.success(request, _("Section added."))
    return redirect("projects:detail", pk=pk)
