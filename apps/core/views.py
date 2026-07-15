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

    # AI muddat agentining oxirgi hisoboti — faqat rahbariyat ko'radi
    ai_report = None
    if request.user.is_superuser or request.user.role in ("admin", "manager"):
        from apps.ai_agents.models import AILog

        ai_report = (
            AILog.objects.filter(agent="deadline", status=AILog.Status.SUCCESS)
            .exclude(response="")
            .first()
        )

    # So'nggi faollik — hujjatlar ustidagi amallar jurnali
    from apps.documents.models import AuditLog

    recent_activity = AuditLog.objects.select_related("user").order_by("-created_at")[:8]

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
        "ai_report": ai_report,
        "recent_activity": recent_activity,
    })


@login_required
def global_search(request):
    """Loyihalar, vazifalar va hujjatlar bo'ylab umumiy qidiruv."""
    query = (request.GET.get("q") or "").strip()
    projects = tasks = documents = []
    if len(query) >= 2:
        visible = visible_projects_for(request.user)
        projects = visible.filter(name__icontains=query)[:10]
        tasks = (
            Task.objects.filter(project__in=visible, title__icontains=query)
            .select_related("project")[:10]
        )
        documents = (
            Document.objects.filter(project__in=visible, name__icontains=query)
            .select_related("project")[:10]
        )
    return render(request, "core/search_results.html", {
        "query": query,
        "projects": projects,
        "tasks": tasks,
        "documents": documents,
    })


@require_POST
def set_dark_mode(request):
    value = "1" if request.POST.get("dark_mode") == "1" else "0"
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    response = redirect(next_url)
    response.set_cookie("dark_mode", value, max_age=60 * 60 * 24 * 365)
    return response
