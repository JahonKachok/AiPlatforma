from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.documents.models import Document, DocumentStatus
from apps.projects.models import Project
from apps.projects.permissions import visible_projects_for
from apps.tasks.models import Task


@login_required
def dashboard(request):
    projects = visible_projects_for(request.user)
    tasks = Task.objects.filter(project__in=projects)
    documents = Document.objects.filter(project__in=projects)
    today = timezone.now().date()

    return render(request, "core/dashboard.html", {
        "active_projects_count": projects.filter(status=Project.Status.ACTIVE).count(),
        "in_progress_tasks_count": tasks.filter(status=Task.Status.IN_PROGRESS).count(),
        "pending_approvals_count": documents.filter(status=DocumentStatus.REVIEW).count(),
        "overdue_tasks_count": tasks.filter(deadline__lt=today).exclude(
            status__in=[Task.Status.COMPLETED, Task.Status.APPROVED]
        ).count(),
        "recent_projects": projects.order_by("-created_at")[:5],
        "recent_tasks": tasks.select_related("assignee", "project").order_by("-created_at")[:6],
        "team": User.objects.filter(is_active=True)[:6],
    })


@require_POST
def set_dark_mode(request):
    value = "1" if request.POST.get("dark_mode") == "1" else "0"
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    response = redirect(next_url)
    response.set_cookie("dark_mode", value, max_age=60 * 60 * 24 * 365)
    return response
