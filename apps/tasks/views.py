import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.documents.models import AuditLog
from apps.notifications.services import notify_user
from apps.projects.permissions import ensure_project_member, visible_projects_for

from .forms import TaskAttachmentForm, TaskCommentForm, TaskForm
from .models import Task, TaskAttachment, TaskComment


def _visible_tasks(user):
    return Task.objects.filter(project__in=visible_projects_for(user)).select_related(
        "project", "assignee", "creator"
    )


@login_required
def task_board(request):
    tasks = _visible_tasks(request.user)

    project_id = request.GET.get("project")
    if project_id:
        tasks = tasks.filter(project_id=project_id)
    assignee_id = request.GET.get("assignee")
    if assignee_id:
        tasks = tasks.filter(assignee_id=assignee_id)
    search = request.GET.get("search")
    if search:
        tasks = tasks.filter(title__icontains=search)

    view = request.GET.get("view", "kanban")
    all_tasks = _visible_tasks(request.user)
    stat_cards = [
        {"label": _("Total"), "value": all_tasks.count()},
        {"label": _("In progress"), "value": all_tasks.filter(status=Task.Status.IN_PROGRESS).count(),
         "color": "text-blue-600 dark:text-blue-400"},
        {"label": _("Completed"), "value": all_tasks.filter(status=Task.Status.COMPLETED).count(),
         "color": "text-green-600 dark:text-green-400"},
        {"label": _("Overdue"), "value": all_tasks.filter(
            deadline__lt=date.today()).exclude(status=Task.Status.COMPLETED).count(),
         "color": "text-red-600 dark:text-red-400"},
    ]
    context = {
        "view": view,
        "project_id": project_id or "",
        "assignee_id": assignee_id or "",
        "search": search or "",
        "projects": visible_projects_for(request.user),
        "assignees": User.objects.filter(is_active=True),
        "stat_cards": stat_cards,
    }

    if view == "list":
        context["tasks"] = tasks
    elif view == "calendar":
        year = int(request.GET.get("year", date.today().year))
        month = int(request.GET.get("month", date.today().month))
        cal = calendar.Calendar(firstweekday=0)
        month_days = list(cal.itermonthdates(year, month))
        tasks_by_day = {}
        for task in tasks.filter(deadline__year=year, deadline__month=month):
            tasks_by_day.setdefault(task.deadline, []).append(task)
        prev_month_date = date(year, month, 1) - timedelta(days=1)
        next_month_date = date(year, month, 28) + timedelta(days=7)
        context.update({
            "month_days": month_days,
            "tasks_by_day": tasks_by_day,
            "current_month": date(year, month, 1),
            "prev_year": prev_month_date.year, "prev_month": prev_month_date.month,
            "next_year": next_month_date.year, "next_month": next_month_date.month,
            "today": date.today(),
        })
    else:
        context["columns"] = [(value, label, tasks.filter(status=value)) for value, label in Task.Status.choices]

    return render(request, "tasks/task_board.html", context)


@login_required
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST)
        form.fields["project"].queryset = visible_projects_for(request.user)
        if form.is_valid():
            task = form.save(commit=False)
            task.creator = request.user
            task.save()
            AuditLog.log(obj=task, action="created", user=request.user)
            if task.assignee:
                ensure_project_member(task.project, task.assignee)
            if task.assignee and task.assignee_id != request.user.id:
                notify_user(
                    task.assignee, "task", _("New task assigned"),
                    _('You were assigned to "%(title)s".') % {"title": task.title},
                    link=f"/tasks/{task.pk}/",
                )
            messages.success(request, _("Task created."))
            return redirect("tasks:detail", pk=task.pk)
    else:
        project_id = request.GET.get("project")
        initial = {"project": project_id} if project_id else {}
        form = TaskForm(initial=initial)
        form.fields["project"].queryset = visible_projects_for(request.user)
    return render(request, "tasks/task_form.html", {"form": form, "is_create": True})


@login_required
def task_detail(request, pk):
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    if request.method == "POST" and "content" in request.POST:
        comment_form = TaskCommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.task = task
            comment.user = request.user
            comment.save()
            if task.assignee and task.assignee_id != request.user.id:
                notify_user(
                    task.assignee, "comment", _("New comment"),
                    _('%(user)s commented on "%(title)s".') % {"user": request.user.get_short_name(), "title": task.title},
                    link=f"/tasks/{task.pk}/",
                )
            return redirect("tasks:detail", pk=pk)
    else:
        comment_form = TaskCommentForm()

    return render(request, "tasks/task_detail.html", {
        "task": task,
        "comment_form": comment_form,
        "attachment_form": TaskAttachmentForm(),
        "statuses": Task.Status.choices,
    })


@login_required
def task_update(request, pk):
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    if request.method == "POST":
        old_status = task.status
        old_assignee_id = task.assignee_id
        form = TaskForm(request.POST, instance=task, project=task.project)
        form.fields["project"].queryset = visible_projects_for(request.user)
        if form.is_valid():
            task = form.save()
            AuditLog.log(obj=task, action="updated", user=request.user)
            if task.assignee:
                ensure_project_member(task.project, task.assignee)
            if task.assignee and task.assignee_id != old_assignee_id and task.assignee_id != request.user.id:
                notify_user(
                    task.assignee, "task", _("Task assigned to you"),
                    _('You were assigned to "%(title)s".') % {"title": task.title},
                    link=f"/tasks/{task.pk}/",
                )
            elif task.status != old_status and task.assignee and task.assignee_id != request.user.id:
                notify_user(
                    task.assignee, "task", _("Task status changed"),
                    _('"%(title)s" is now %(status)s.') % {"title": task.title, "status": task.get_status_display()},
                    link=f"/tasks/{task.pk}/",
                )
            messages.success(request, _("Task updated."))
            return redirect("tasks:detail", pk=pk)
    else:
        form = TaskForm(instance=task, project=task.project)
        form.fields["project"].queryset = visible_projects_for(request.user)
    return render(request, "tasks/task_form.html", {"form": form, "task": task, "is_create": False})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    if request.method == "POST":
        task.delete()
        messages.success(request, _("Task deleted."))
        return redirect("tasks:board")
    return render(request, "tasks/task_confirm_delete.html", {"task": task})


@require_POST
@login_required
def task_update_status(request, pk):
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    status = request.POST.get("status")
    if status in Task.Status.values:
        task.status = status
        task.save(update_fields=["status", "updated_at"])
        AuditLog.log(obj=task, action="status_changed", user=request.user, details={"status": status})
        if task.assignee and task.assignee_id != request.user.id:
            notify_user(
                task.assignee, "task", _("Task status changed"),
                _('"%(title)s" is now %(status)s.') % {"title": task.title, "status": task.get_status_display()},
                link=f"/tasks/{task.pk}/",
            )
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "status": task.status})
    return redirect("tasks:detail", pk=pk)


@login_required
def task_comment_delete(request, pk, comment_id):
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    comment = get_object_or_404(TaskComment, pk=comment_id, task=task)
    if comment.user_id != request.user.id and not request.user.is_superuser:
        raise PermissionDenied
    comment.delete()
    return redirect("tasks:detail", pk=pk)


@login_required
def task_attachment_upload(request, pk):
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    if request.method == "POST":
        form = TaskAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.task = task
            attachment.user = request.user
            attachment.filename = attachment.file.name
            attachment.file_size = attachment.file.size
            attachment.save()
    return redirect("tasks:detail", pk=pk)


@login_required
def task_attachment_delete(request, pk, attachment_id):
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    attachment = get_object_or_404(TaskAttachment, pk=attachment_id, task=task)
    if attachment.user_id != request.user.id and not request.user.is_superuser:
        raise PermissionDenied
    attachment.file.delete(save=False)
    attachment.delete()
    return redirect("tasks:detail", pk=pk)
