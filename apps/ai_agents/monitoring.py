from collections import Counter
from datetime import datetime, time, timedelta

from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.worker.models import JobKind, JobStatus, WorkerJob, WorkerNode
from apps.worker.services import ONLINE_WITHIN, is_online

from .models import AILog, PendingAction
from .orchestrator import PENDING_TTL


AGENT_GROUPS = (
    (_("Team"), (
        ("dispatcher", _("Task dispatcher"), _("Collects progress updates and requests intermediate files.")),
        ("kpi", _("KPI analyst"), _("Calculates points and ranks accepted work.")),
    )),
    (_("Finance and office"), (
        ("treasurer", _("Treasurer"), _("Prepares project payments for confirmation.")),
        ("quartermaster", _("Office manager"), _("Records office expenses and reminds staff about recurring payments.")),
    )),
    (_("Drawings"), (
        ("translator", _("Drawing translator"), _("Translates DWG text and spreadsheet cells.")),
        ("printer", _("PDF printer"), _("Fills existing stamps and merges drawing layouts into a PDF.")),
        ("gost", _("GOST formatter"), _("Applies the approved page setup, title block and fonts to DWG layouts.")),
        ("norm_control", _("Standards checker"), _("Checks sheet size, margins and overlapping text.")),
    )),
    (_("Documents"), (
        ("archivist", _("Archivist"), _("Finds project documents and archives revisions in Google Drive.")),
        ("secretary", _("Contract secretary"), _("Drafts documents and sends PDFs for signature.")),
    )),
)

AGENT_NAMES = {key: name for _, agents in AGENT_GROUPS for key, name, _description in agents}
JOB_KINDS = {
    "gost": (JobKind.GOST_FORMAT,),
    "translator": (JobKind.DWG_TRANSLATE, JobKind.XLSX_TRANSLATE),
    "printer": (JobKind.DWG_PRINT,), "norm_control": (JobKind.NORM_CONTROL,),
    "secretary": (JobKind.DOCX_TO_PDF,),
}


def office_stations():
    now = timezone.now()
    calls = Counter()
    for agent, total in (AILog.objects.filter(created_at__gte=now - timedelta(hours=24), created_at__lte=now)
                         .order_by().values_list("agent").annotate(n=Count("pk"))):
        calls[agent.removeprefix("worker:")] += total
    jobs = {(kind, status): total for kind, status, total in
            WorkerJob.objects.filter(status__in=(JobStatus.RUNNING, JobStatus.QUEUED))
            .order_by().values_list("kind", "status").annotate(n=Count("pk"))}
    pending = dict(PendingAction.objects.filter(done_at__isnull=True, created_at__gte=now - PENDING_TTL)
                   .order_by().values_list("kind").annotate(n=Count("pk")))
    payment_kinds = {"treasurer": "project_operation", "quartermaster": "office_expense"}
    online_kinds = {kind for kinds in WorkerNode.objects.filter(last_seen__gte=now - ONLINE_WITHIN)
                    .values_list("kinds", flat=True) for kind in kinds}
    links = {"dispatcher": reverse("pult:section_tasks"), "kpi": reverse("pult:section_kpi")}
    stations = []
    for group, agents in AGENT_GROUPS:
        for key, name, description in agents:
            kinds = JOB_KINDS.get(key, ())
            running = sum(jobs.get((kind, JobStatus.RUNNING), 0) for kind in kinds)
            queued = sum(jobs.get((kind, JobStatus.QUEUED), 0) for kind in kinds)
            waiting = pending.get(payment_kinds.get(key), 0)
            if key == "dispatcher":
                waiting = pending.get("task_create", 0) + pending.get("task_status", 0)
            state = "quiet"
            if running:
                state = "running"
            elif waiting or queued:
                state = "waiting"
            elif kinds and not online_kinds.intersection(kinds):
                state = "offline"
            feed = "jobs" if kinds else "calls"
            stations.append({
                "key": key, "name": str(name), "group": str(group), "description": str(description),
                "state": state, "calls": calls[key], "running": running, "queued": queued, "pending": waiting,
                "link": links.get(key, f"{reverse('ai_agents:dashboard')}?feed={feed}&agent={key}#activity"),
            })
    return {"stations": stations, "updated": now.isoformat()}


def monitor_context(params):
    now = timezone.now()
    today = timezone.localdate(now)
    start = today - timedelta(days=6)
    midnight = timezone.make_aware(datetime.combine(start, time.min))
    calls = AILog.objects.filter(created_at__gte=midnight, created_at__lte=now)
    daily = dict(calls.order_by().annotate(day=TruncDate("created_at"))
                 .values_list("day").annotate(total=Count("pk")))
    days = [{"date": start + timedelta(days=i), "count": daily.get(start + timedelta(days=i), 0)}
            for i in range(7)]

    jobs = WorkerJob.objects.select_related("document").order_by("-created_at", "-pk")
    pending = PendingAction.objects.filter(done_at__isnull=True, created_at__gte=now - PENDING_TTL)
    job_counts = dict(jobs.order_by().values_list("status").annotate(total=Count("pk")))
    feeds = {
        "calls": AILog.objects.defer("system", "prompt", "response", "error").order_by("-created_at", "-pk"),
        "jobs": jobs,
        "pending": pending.select_related("user").order_by("-created_at", "-pk"),
    }
    feed = params.get("feed", "calls")
    if feed not in feeds:
        feed = "calls"
    agent = params.get("agent", "")
    records = feeds[feed]
    if feed == "calls" and agent in AGENT_NAMES:
        records = records.filter(agent__in=(agent, f"worker:{agent}"))
    elif feed == "jobs" and agent in JOB_KINDS:
        records = records.filter(kind__in=JOB_KINDS[agent])
    else:
        agent = ""
    return {
        "agent_groups": AGENT_GROUPS, "days": days, "week_total": sum(daily.values()),
        "peak": max(daily.values(), default=1), "worker_online": is_online(),
        "queued": job_counts.get(JobStatus.QUEUED, 0), "running": job_counts.get(JobStatus.RUNNING, 0),
        "pending_count": pending.count(), "feed": feed,
        "job_agents": JOB_KINDS, "agent": agent, "selected_name": AGENT_NAMES.get(agent),
        "events": Paginator(records, 12).get_page(params.get("page")),
    }
