"""Ishchi kompyuter API'si. Kirish — admin panelda o'rnatilgan WORKER_TOKEN
(``Authorization: Bearer <token>``). Brauzer sessiyasi ishlatilmaydi."""
import hmac
import json
from functools import wraps

from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from apps.core.runtime_config import get_config

from . import services
from .models import JobStatus, WorkerJob

MAX_RESULT_BYTES = 200 * 1024 * 1024


def worker_api(view):
    @csrf_exempt
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        token = get_config("WORKER_TOKEN")
        auth = request.headers.get("Authorization", "")
        if not token or not hmac.compare_digest(auth.encode(), f"Bearer {token}".encode()):
            return JsonResponse({"ok": False, "error": "unauthorized"}, status=401)
        return view(request, *args, **kwargs)
    return wrapper


def _body(request):
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


@worker_api
@require_POST
def heartbeat(request):
    data = _body(request)
    services.heartbeat(str(data.get("worker") or "worker"), data.get("kinds"), data.get("version", ""))
    return JsonResponse({"ok": True})


@worker_api
@require_POST
def claim(request):
    from apps.documents.services import file_basename

    data = _body(request)
    worker = str(data.get("worker") or "worker")
    services.heartbeat(worker, data.get("kinds"), data.get("version", ""))
    job = services.claim(worker, data.get("kinds") or None)
    if job is None:
        return JsonResponse({"ok": True, "job": None})
    doc = job.document
    section = doc.section
    return JsonResponse({"ok": True, "job": {
        "id": str(job.pk), "kind": job.kind, "params": job.params,
        "file_name": file_basename(job.version),
        "project": doc.project.name,
        "discipline": section.discipline.code if section else "",
        "object": section.sub_object.name if section and section.sub_object else "",
        "executor": job.requested_by.full_name if job.requested_by else "",
    }})


@worker_api
@require_GET
def job_input(request, pk):
    from apps.documents.archivist import open_file
    from apps.documents.services import file_basename

    job = get_object_or_404(WorkerJob, pk=pk, status=JobStatus.RUNNING)
    try:
        handle = open_file(job.version)
    except FileNotFoundError:
        raise Http404
    return FileResponse(handle, as_attachment=True, filename=file_basename(job.version))


@worker_api
@require_POST
def job_result(request, pk):
    job = get_object_or_404(WorkerJob, pk=pk, status=JobStatus.RUNNING)
    ok = request.POST.get("ok") == "1"
    try:
        result = json.loads(request.POST.get("result") or "{}")
    except ValueError:
        result = {}
    upload, source = request.FILES.get("file"), request.FILES.get("source")
    if any(f is not None and f.size > MAX_RESULT_BYTES for f in (upload, source)):
        return JsonResponse({"ok": False, "error": "file too large"}, status=413)
    services.finish(job, ok, result if isinstance(result, dict) else {}, upload.name if upload else "",
                    upload.read() if upload is not None else None, request.POST.get("error", ""),
                    source_data=source.read() if source is not None else None)
    return JsonResponse({"ok": True})


@worker_api
@require_POST
def ai(request):
    """Kompyuterdagi agentlar (tarjimon, shtamp, normokontrol) uchun AI proksi:
    Claude kaliti kompyuterda saqlanmaydi, har chaqiruv AILog'ga yoziladi va
    so'rovchining tuzatishlari (AgentMemory) promptga qo'shiladi."""
    from apps.ai_agents.orchestrator import _memory_rules
    from apps.ai_agents.prompts import AGENTS
    from apps.ai_agents.services import ask_json

    data = _body(request)
    agent = data.get("agent")
    if agent not in ("translator", "printer", "norm_control") or not isinstance(data.get("input"), (dict, list)):
        return JsonResponse({"ok": False, "error": "bad request"}, status=400)
    job = WorkerJob.objects.filter(pk=data.get("job"), status=JobStatus.RUNNING).select_related("requested_by").first()
    if job is None:
        return JsonResponse({"ok": False, "error": "no such running job"}, status=404)
    prompt, schema, _where = AGENTS[agent]
    rules = _memory_rules(job.requested_by, agent) if job.requested_by else ""
    payload = json.dumps(data["input"], ensure_ascii=False, separators=(",", ":"))
    answer = ask_json(prompt + rules, payload, schema, agent=f"worker:{agent}", max_tokens=8000)
    if answer is None:
        return JsonResponse({"ok": False, "error": "ai unavailable"}, status=503)
    return JsonResponse({"ok": True, "data": answer})
