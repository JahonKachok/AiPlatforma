import calendar
import json
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
from apps.projects.models import Section, SubObject
from apps.projects.permissions import ensure_project_member, visible_projects_for

from .forms import TaskAttachmentForm, TaskCommentForm, TaskForm
from .models import Task, TaskAttachment, TaskComment
from .permissions import (
    allowed_status_targets, can_change_task_status, is_privileged, resolve_reviewer, reviewer_candidates,
)
from .services import submit_task_for_approval


def _visible_tasks(user):
    return Task.objects.filter(project__in=visible_projects_for(user)).select_related(
        "project", "assignee", "creator", "section", "section__sub_object"
    )


def _task_form_cascade_json(user):
    """JSON data the task form's JS uses to cascade Project -> Object -> Pod
    object -> Section, and to narrow the Assignee list down to employees who
    actually have the selected section's discipline (e.g. only architects once
    an AR section is picked)."""
    projects = visible_projects_for(user)
    sub_objects = [
        {"id": str(so.pk), "project_id": str(so.project_id), "parent_id": str(so.parent_id) if so.parent_id else None,
         "name": so.name}
        for so in SubObject.objects.filter(project__in=projects)
    ]
    sections = [
        {"id": str(s.pk), "project_id": str(s.project_id),
         "sub_object_id": str(s.sub_object_id) if s.sub_object_id else None,
         "discipline_id": str(s.discipline_id)}
        for s in Section.objects.filter(project__in=projects).select_related("discipline")
    ]
    discipline_users = {}
    for user_obj in User.objects.filter(is_active=True).prefetch_related("disciplines"):
        for discipline in user_obj.disciplines.all():
            discipline_users.setdefault(str(discipline.id), []).append(
                {"id": str(user_obj.id), "name": user_obj.full_name or user_obj.email}
            )
    return json.dumps({
        "subObjects": sub_objects, "sections": sections, "disciplineUsers": discipline_users,
    })


@login_required
def task_board(request):
    tasks = _visible_tasks(request.user)

    project_id = request.GET.get("project")
    if project_id:
        tasks = tasks.filter(project_id=project_id)
    object_id = request.GET.get("object")
    if object_id:
        tasks = tasks.filter(section__sub_object_id=object_id)
    subobject_id = request.GET.get("subobject")
    if subobject_id:
        tasks = tasks.filter(section_id=subobject_id)
    assignee_id = request.GET.get("assignee")
    if assignee_id:
        tasks = tasks.filter(assignee_id=assignee_id)
    search = request.GET.get("search")
    if search:
        tasks = tasks.filter(title__icontains=search)

    objects_qs = SubObject.objects.none()
    subobjects_qs = Section.objects.none()
    if project_id:
        objects_qs = SubObject.objects.filter(project_id=project_id)
        subobjects_qs = Section.objects.filter(project_id=project_id)
        if object_id:
            subobjects_qs = subobjects_qs.filter(sub_object_id=object_id)

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
        "object_id": object_id or "",
        "subobject_id": subobject_id or "",
        "assignee_id": assignee_id or "",
        "search": search or "",
        "projects": visible_projects_for(request.user),
        "objects": objects_qs,
        "subobjects": subobjects_qs,
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
        columns = [(value, label, list(tasks.filter(status=value))) for value, label in Task.Status.choices]
        context["columns"] = columns
        context["task_allowed_targets"] = {
            task.pk: sorted(allowed_status_targets(request.user, task))
            for _value, _label, column_tasks in columns
            for task in column_tasks
        }

    return render(request, "tasks/task_board.html", context)


@login_required
def task_create(request):
    if request.method == "POST":
        form = TaskForm(request.POST, user=request.user)
        form.fields["project"].queryset = visible_projects_for(request.user)
        form.fields["section"].queryset = Section.objects.filter(project__in=visible_projects_for(request.user))
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
        form = TaskForm(initial=initial, user=request.user)
        form.fields["project"].queryset = visible_projects_for(request.user)
        form.fields["section"].queryset = Section.objects.filter(project__in=visible_projects_for(request.user))
    return render(request, "tasks/task_form.html", {
        "form": form, "is_create": True,
        "task_form_cascade_json": _task_form_cascade_json(request.user),
    })


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

    reviewer = resolve_reviewer(task)
    is_reviewer = task.status == Task.Status.REVIEW and (
        is_privileged(request.user) or (reviewer is not None and reviewer.id == request.user.id)
    )
    # "Review" gets its own dialog (you pick who checks it), so it is not one
    # of the plain one-click status buttons.
    next_statuses = [
        (value, label) for value, label in Task.Status.choices
        if value not in (Task.Status.REVISION, Task.Status.REVIEW)
        and can_change_task_status(request.user, task, value)
    ]
    can_send_for_review = can_change_task_status(request.user, task, Task.Status.REVIEW)

    return render(request, "tasks/task_detail.html", {
        "task": task,
        "comment_form": comment_form,
        "attachment_form": TaskAttachmentForm(),
        "next_statuses": next_statuses,
        "reviewer": reviewer,
        "is_reviewer": is_reviewer,
        "can_send_for_review": can_send_for_review,
        "reviewer_candidates": reviewer_candidates().exclude(pk=request.user.pk),
        "revision_form": TaskCommentForm(),
    })


@login_required
def task_update(request, pk):
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    if request.method == "POST":
        old_status = task.status
        old_assignee_id = task.assignee_id
        form = TaskForm(request.POST, instance=task, project=task.project, user=request.user)
        form.fields["project"].queryset = visible_projects_for(request.user)
        form.fields["section"].queryset = Section.objects.filter(project__in=visible_projects_for(request.user))
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
        form = TaskForm(instance=task, project=task.project, user=request.user)
        form.fields["project"].queryset = visible_projects_for(request.user)
        form.fields["section"].queryset = Section.objects.filter(project__in=visible_projects_for(request.user))
    return render(request, "tasks/task_form.html", {
        "form": form, "task": task, "is_create": False,
        "task_form_cascade_json": _task_form_cascade_json(request.user),
    })


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
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    if status not in Task.Status.values:
        if is_ajax:
            return JsonResponse({"ok": False, "error": _("Unknown status.")}, status=400)
        messages.error(request, _("Unknown status."))
        return redirect("tasks:detail", pk=pk)

    if not can_change_task_status(request.user, task, status):
        error = _("You don't have permission to move this task to that status.")
        if is_ajax:
            return JsonResponse({"ok": False, "error": str(error)}, status=403)
        messages.error(request, error)
        return redirect("tasks:detail", pk=pk)

    comment = (request.POST.get("content") or "").strip()
    if status == Task.Status.REVISION and not comment:
        error = _("A comment is required when sending a task back for revision.")
        if is_ajax:
            return JsonResponse({"ok": False, "error": str(error)}, status=400)
        messages.error(request, error)
        return redirect("tasks:detail", pk=pk)

    update_fields = ["status", "updated_at"]
    chosen_reviewer = None
    if status == Task.Status.REVIEW:
        reviewer_id = request.POST.get("reviewer")
        if reviewer_id:
            chosen_reviewer = reviewer_candidates().filter(pk=reviewer_id).first()
            if chosen_reviewer is None:
                error = _("Pick who should check this task.")
                if is_ajax:
                    return JsonResponse({"ok": False, "error": str(error)}, status=400)
                messages.error(request, error)
                return redirect("tasks:detail", pk=pk)
            task.reviewer = chosen_reviewer
            update_fields.append("reviewer")

    task.status = status
    task.save(update_fields=update_fields)
    if chosen_reviewer is not None:
        ensure_project_member(task.project, chosen_reviewer)
        if chosen_reviewer.id != request.user.id:
            notify_user(
                chosen_reviewer, "task", _("Task sent to you for review"),
                _('"%(title)s" is waiting for your review.') % {"title": task.title},
                link=f"/tasks/{task.pk}/",
            )
        messages.success(
            request,
            _("Sent for review to %(user)s.") % {"user": chosen_reviewer.get_short_name()},
        )
    if comment:
        TaskComment.objects.create(task=task, user=request.user, content=comment)
    AuditLog.log(obj=task, action="status_changed", user=request.user, details={"status": status})
    if task.assignee and task.assignee_id != request.user.id:
        notify_user(
            task.assignee, "task", _("Task status changed"),
            _('"%(title)s" is now %(status)s.') % {"title": task.title, "status": task.get_status_display()},
            link=f"/tasks/{task.pk}/",
        )
    if is_ajax:
        return JsonResponse({"ok": True, "status": task.status})
    return redirect("tasks:detail", pk=pk)


@require_POST
@login_required
def task_send_for_approval(request, pk):
    """The reviewer passes a checked task on to the project's GIP. The task
    stays in review until the GIP signs it off in the Approvals section — only
    then does it become approved."""
    task = get_object_or_404(_visible_tasks(request.user), pk=pk)
    reviewer = resolve_reviewer(task)
    is_reviewer = is_privileged(request.user) or (reviewer is not None and reviewer.id == request.user.id)
    if not is_reviewer or task.status != Task.Status.REVIEW:
        raise PermissionDenied

    document = submit_task_for_approval(task, request.user)
    if document is None:
        messages.error(request, _("This project has no GIP assigned to sign work off."))
    else:
        approver = document.approval_stages.last().reviewer
        messages.success(
            request,
            _("Sent to %(user)s for approval. The task will be approved once they sign it off.")
            % {"user": approver.get_short_name()},
        )
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
