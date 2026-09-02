from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import content_disposition_header, url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.static import serve

from apps.accounts.models import User
from apps.documents.models import ApprovalStage, ApprovalStatus, AuditLog, Document, DocumentStatus
from apps.projects.models import Project
from apps.projects.permissions import visible_projects_for
from apps.projects.queries import attach_card_fields, card_queryset
from apps.tasks.models import Task

SPARK_WEEKS = 8
DASHBOARD_PROJECTS = 5
DASHBOARD_TEAM = 6
DASHBOARD_ACTIVITY = 8


def _week_starts(today, weeks=SPARK_WEEKS):
    """Monday of each of the last `weeks` weeks, oldest first."""
    this_monday = today - timedelta(days=today.weekday())
    return [this_monday - timedelta(weeks=offset) for offset in range(weeks - 1, -1, -1)]


def _bucket_by_week(dates, week_starts):
    """Count `dates` into the week buckets. Returns a plain list of ints, which
    is all the sparkline needs — no interpolation, no invented points."""
    counts = [0] * len(week_starts)
    last = len(week_starts) - 1
    for value in dates:
        if value is None or value < week_starts[0]:
            continue
        for index in range(last, -1, -1):
            if value >= week_starts[index]:
                counts[index] += 1
                break
    return counts


def _visible_audit_log(user, projects):
    """Activity is scoped the same way everything else is.

    AuditLog rows point at a Project, Task or Document through a generic
    foreign key, so the only way to filter them is by (content_type, object_id)
    against the ids the user may see. Without this the dashboard listed every
    action in the system, including on projects the user has no access to.
    """
    # Admins and managers may see every project anyway, so skip building id
    # lists for them — that is also the case where the lists would be largest.
    if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.MANAGER):
        return AuditLog.objects.select_related("user")

    project_ids = list(projects.values_list("pk", flat=True))
    if not project_ids:
        return AuditLog.objects.none()

    task_ids = Task.objects.filter(project_id__in=project_ids).values_list("pk", flat=True)
    document_ids = Document.objects.filter(project_id__in=project_ids).values_list("pk", flat=True)

    scopes = [
        (ContentType.objects.get_for_model(Project), [str(pk) for pk in project_ids]),
        (ContentType.objects.get_for_model(Task), [str(pk) for pk in task_ids]),
        (ContentType.objects.get_for_model(Document), [str(pk) for pk in document_ids]),
    ]
    condition = Q(pk__in=[])
    for content_type, ids in scopes:
        if ids:
            condition |= Q(content_type=content_type, object_id__in=ids)
    return AuditLog.objects.filter(condition).select_related("user")


def _latest_ai_report(user):
    """The AI panel is an optional module — a failure there must not take the
    whole dashboard down with it (each widget stands on its own)."""
    if not (user.is_superuser or user.role in (User.Role.ADMIN, User.Role.MANAGER)):
        return None
    try:
        from apps.ai_agents.models import AILog

        return (
            AILog.objects.filter(agent="deadline", status=AILog.Status.SUCCESS)
            .exclude(response="")
            .first()
        )
    except Exception:
        return None


@login_required
def dashboard(request):
    user = request.user
    projects = visible_projects_for(user)
    tasks = Task.objects.filter(project__in=projects)
    documents = Document.objects.filter(project__in=projects)

    now = timezone.now()
    today = timezone.localdate()
    week_starts = _week_starts(today)
    month_ago = today - timedelta(days=30)
    week_ahead = today + timedelta(days=7)

    open_tasks = tasks.exclude(status__in=[Task.Status.COMPLETED, Task.Status.APPROVED])
    overdue_tasks = open_tasks.filter(deadline__lt=today)
    pending_documents = documents.filter(status=DocumentStatus.REVIEW)

    # --- KPI cards -------------------------------------------------------
    # Every figure, hint and sparkline point below is derived from the rows the
    # user may see. Where the data cannot support a comparison (there is no
    # status history in this schema, so "+12% vs last month" is not knowable)
    # the card shows a second real measure instead of an invented percentage.
    active_projects = projects.filter(status=Project.Status.ACTIVE)
    in_progress_tasks = tasks.filter(status=Task.Status.IN_PROGRESS)

    project_weeks = _bucket_by_week(
        [d.date() for d in projects.values_list("created_at", flat=True) if d],
        week_starts,
    )
    task_weeks = _bucket_by_week(
        [d.date() for d in tasks.values_list("created_at", flat=True) if d],
        week_starts,
    )
    approval_weeks = _bucket_by_week(
        [
            d.date()
            for d in ApprovalStage.objects.filter(document__in=documents).values_list(
                "created_at", flat=True
            )
            if d
        ],
        week_starts,
    )
    # For "overdue" the meaningful series is when the deadlines fell, counted
    # only for tasks that are still open — i.e. the backlog as it built up.
    overdue_weeks = _bucket_by_week(
        list(overdue_tasks.values_list("deadline", flat=True)), week_starts,
    )

    kpi_cards = [
        {
            "key": "projects", "tone": "blue",
            "label": _("Active projects"),
            "value": active_projects.count(),
            "hint": _("%(n)s created in 30 days") % {
                "n": projects.filter(created_at__date__gte=month_ago).count()
            },
            "spark": project_weeks,
            "url": f"{reverse('projects:list')}?status=active",
        },
        {
            "key": "tasks", "tone": "green",
            "label": _("Tasks in progress"),
            "value": in_progress_tasks.count(),
            "hint": _("%(n)s assigned to you") % {
                "n": in_progress_tasks.filter(assignee=user).count()
            },
            "spark": task_weeks,
            "url": reverse("tasks:board"),
        },
        {
            "key": "approvals", "tone": "amber",
            "label": _("Pending approvals"),
            "value": pending_documents.count(),
            "hint": _("%(n)s waiting for you") % {
                "n": ApprovalStage.objects.filter(
                    reviewer=user, status=ApprovalStatus.PENDING, document__in=documents,
                ).count()
            },
            "spark": approval_weeks,
            "url": reverse("documents:approvals"),
        },
        {
            "key": "overdue", "tone": "red",
            "label": _("Overdue tasks"),
            "value": overdue_tasks.count(),
            "hint": _("%(n)s due this week") % {
                "n": open_tasks.filter(deadline__gte=today, deadline__lte=week_ahead).count()
            },
            "spark": overdue_weeks,
            "url": f"{reverse('tasks:board')}?view=list",
        },
    ]

    # --- Active projects list -------------------------------------------
    recent_projects = list(
        card_queryset(active_projects).order_by("-updated_at")[:DASHBOARD_PROJECTS]
    )
    attach_card_fields(recent_projects, today=today)

    # --- Team ------------------------------------------------------------
    # Colleagues on the projects this user can see, not the whole directory —
    # for admins and managers visible_projects_for() is everything anyway.
    team = (
        User.objects.filter(is_active=True, project_memberships__project__in=projects)
        .exclude(pk=user.pk)
        .distinct()
        .prefetch_related("disciplines")[:DASHBOARD_TEAM]
    )

    ai_report = _latest_ai_report(user)

    return render(request, "core/dashboard.html", {
        "kpi_cards": kpi_cards,
        "recent_projects": recent_projects,
        "recent_tasks": tasks.select_related("assignee", "project").order_by("-created_at")[:6],
        "team": team,
        "ai_report": ai_report,
        # "New" means exactly that: produced in the last 24 hours. No badge
        # is shown for an old report.
        "ai_report_is_new": bool(ai_report and ai_report.created_at >= now - timedelta(days=1)),
        "recent_activity": _visible_audit_log(user, projects)[:DASHBOARD_ACTIVITY],
        "now": now,
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
    # Ochiq redirect (open redirect) bo'lmasligi uchun faqat shu saytga
    # tegishli manzillarga qaytamiz — aks holda ?next=//evil.example bilan
    # foydalanuvchini tashqi saytga uzatib yuborish mumkin edi.
    candidate = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    if not url_has_allowed_host_and_scheme(
        candidate, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        candidate = "/"
    response = redirect(candidate)
    response.set_cookie(
        "dark_mode", value, max_age=60 * 60 * 24 * 365,
        samesite="Lax", secure=request.is_secure(),
    )
    return response


# Brauzerda o'z-o'zidan ochilishiga ruxsat berilgan turlar. Qolgan hamma narsa
# (jumladan .html va .svg — ular skript ijro eta oladi) majburan yuklab olinadi,
# shunda yuklangan fayl saytning o'z domenida XSS'ga aylanmaydi.
_INLINE_MEDIA_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


@login_required
def protected_media(request, path):
    """MEDIA_ROOT'dagi fayllarni faqat tizimga kirgan foydalanuvchiga beradi.

    Ilgari /media/ to'g'ridan-to'g'ri nginx (va DEBUG'da Django) orqali ochiq
    tarqatilardi — ya'ni loyiha hujjatlarini havolani bilgan har kim
    autentifikatsiyasiz yuklab olishi mumkin edi. ``django.views.static.serve``
    ``safe_join`` ishlatgani uchun ``../`` bilan katalogdan chiqib ketib
    bo'lmaydi.
    """
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if response.headers.get("Content-Type") not in _INLINE_MEDIA_TYPES:
        # content_disposition_header lotin bo'lmagan nomlarni (masalan
        # "Проекты/...") RFC 5987 bo'yicha kodlaydi — qo'lda yozilgan sarlavha
        # bunday nomlarda UnicodeEncodeError bilan tushib qolardi.
        response.headers["Content-Disposition"] = content_disposition_header(
            as_attachment=True, filename=path.rsplit("/", 1)[-1]
        )
    return response
