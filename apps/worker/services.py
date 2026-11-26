"""Ishchi kompyuter navbati: ish yaratish, berish va natijani qabul qilish.

Natija fayli Arxivarius orqali saqlanadi: shu bo'limda shu nomli hujjat bo'lsa
— uning yangi reviziyasi (eski reviziya Drive'da «Old»ga ko'chadi), bo'lmasa
yangi hujjat. Tarjima fayl nomini o'zgartirmaydi — asl hujjatning reviziyasi.
"""
import logging
from datetime import timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from .models import JobKind, JobStatus, WorkerJob, WorkerNode

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=30)  # osilib qolgan ish qayta navbatga
ONLINE_WITHIN = timedelta(minutes=3)
MAX_ATTEMPTS = 3

# Ish turi -> qabul qilinadigan kirish fayllari
INPUT_EXT = {
    JobKind.GOST_FORMAT: (".dwg",),
    JobKind.DWG_PRINT: (".dwg",),
    JobKind.DWG_TRANSLATE: (".dwg",),
    JobKind.XLSX_TRANSLATE: (".xlsx", ".xlsm"),
    JobKind.DOCX_TO_PDF: (".docx", ".doc"),
    JobKind.NORM_CONTROL: (".pdf", ".dwg"),
}
PDF_OUTPUT = {JobKind.DWG_PRINT, JobKind.DOCX_TO_PDF}


def accepts(kind, filename):
    return (filename or "").lower().endswith(INPUT_EXT[kind])


def create_job(kind, document, user=None, params=None, then=""):
    """Hujjatning joriy reviziyasi bo'yicha ish qo'shadi."""
    version = document.versions.order_by("-revision").first()
    if version is None:
        raise ValueError("document has no revision")
    return WorkerJob.objects.create(kind=kind, document=document, version=version, requested_by=user,
                                    params=params or {}, then=then)


def is_online():
    return WorkerNode.objects.filter(last_seen__gte=timezone.now() - ONLINE_WITHIN).exists()


def heartbeat(name, kinds=None, version=""):
    WorkerNode.objects.update_or_create(name=name[:64], defaults={
        "last_seen": timezone.now(), "kinds": list(kinds or []), "version": str(version)[:32],
    })


@transaction.atomic
def claim(worker, kinds=None):
    """Navbatdagi eng eski ishni shu kompyuterga beradi (bo'lmasa None)."""
    now = timezone.now()
    # Kompyuter ish paytida o'chib qolgan bo'lsa — ish yo'qolmaydi.
    WorkerJob.objects.filter(status=JobStatus.RUNNING, started_at__lt=now - STALE_AFTER,
                             attempts__lt=MAX_ATTEMPTS).update(status=JobStatus.QUEUED)
    qs = WorkerJob.objects.select_for_update(skip_locked=True).filter(status=JobStatus.QUEUED)
    if kinds:
        qs = qs.filter(kind__in=kinds)
    job = qs.order_by("created_at").first()
    if job is None:
        return None
    job.status, job.worker, job.started_at = JobStatus.RUNNING, worker[:64], now
    job.attempts += 1
    job.save(update_fields=["status", "worker", "started_at", "attempts"])
    return job


def _output_name(job, uploaded_name):
    from apps.documents.services import file_basename

    source = file_basename(job.version)
    stem = source.rsplit(".", 1)[0]
    if job.kind == JobKind.NORM_CONTROL:
        return f"{stem}.remarks.xlsx"
    if job.kind in PDF_OUTPUT:
        return f"{stem}.pdf"
    return source  # tarjima: fayl nomi o'zgarmaydi


def _store(job, filename, data):
    from apps.documents.archivist import add_revision, find_same_file
    from apps.documents.models import AuditLog, Document, DocumentVersion

    source = job.document
    upload = ContentFile(data, name=filename)
    user = job.requested_by or source.uploaded_by
    note = f"{job.get_kind_display()} · ishchi kompyuter {job.worker}"
    target = find_same_file(source.project, source.section, filename)
    if target is not None:
        add_revision(target, upload, user, notes=note)
    else:
        target = Document.objects.create(
            name=f"{source.name} (PDF)" if job.kind in PDF_OUTPUT else source.name,
            doc_type=source.doc_type, project=source.project, section=source.section, uploaded_by=user,
            file=upload, file_size=len(data),
        )
        DocumentVersion.objects.create(document=target, version_number=target.version, file=target.file.name,
                                       file_size=target.file_size, uploaded_by=user, notes=note)
    AuditLog.log(obj=target, action="worker_result", user=user, details={"job": str(job.pk), "kind": job.kind})
    return target


def finish(job, ok, result=None, filename="", data=None, error="", source_data=None):
    """Kompyuter natijasini qabul qiladi va kerakli joyga yetkazadi.
    source_data — o'zgartirilgan asl fayl (shtamp to'ldirilgan DWG): asl
    hujjatning yangi reviziyasi bo'ladi."""
    with transaction.atomic():
        job = WorkerJob.objects.select_for_update().get(pk=job.pk)
        if job.status != JobStatus.RUNNING:
            return job
        _store_result(job, ok, result, filename, data, error, source_data)
    if job.status == JobStatus.ERROR:
        _notify(job, f"⚠️ {job.get_kind_display()}: {job.document.name} — {job.error[:300]}")
    elif job.status == JobStatus.DONE:
        _after(job)
    return job


def _store_result(job, ok, result, filename, data, error, source_data):
    job.result = result or {}
    if ok and job.then == "drawing_pipeline":
        if not data or (job.kind == JobKind.NORM_CONTROL and not isinstance(job.result.get("remarks"), list)):
            ok, error = False, "Missing drawing pipeline result"
        elif job.document.versions.filter(revision__gt=job.version.revision).exists():
            ok, error = False, "Source revision changed during processing"
    job.finished_at = timezone.now()
    if not ok:
        job.error = (error or "unknown error")[:4000]
        job.status = JobStatus.QUEUED if job.attempts < MAX_ATTEMPTS and job.result.get("retry") else JobStatus.ERROR
        job.save(update_fields=["result", "finished_at", "error", "status"])
        return
    if source_data:
        from apps.documents.services import file_basename

        _store(job, file_basename(job.version), source_data)
    if data:
        job.result_document = _store(job, _output_name(job, filename), data)
        if job.then == "drawing_pipeline" and job.kind == JobKind.DWG_PRINT:
            revision = job.result_document.versions.get(version_number=job.result_document.version)
            job.result_document.versions.filter(pk=revision.pk).update(mdr_state="pending")
    job.status, job.error = JobStatus.DONE, ""
    job.save(update_fields=["result", "finished_at", "status", "error", "result_document"])
    if job.then == "drawing_pipeline":
        if job.kind in (JobKind.DWG_TRANSLATE, JobKind.GOST_FORMAT):
            following = JobKind.GOST_FORMAT if job.kind == JobKind.DWG_TRANSLATE else JobKind.NORM_CONTROL
            create_job(following, job.result_document, job.requested_by, then=job.then)
        elif job.kind == JobKind.NORM_CONTROL and not any(r["severity"] == "critical" for r in job.result["remarks"]):
            WorkerJob.objects.create(kind=JobKind.DWG_PRINT, document=job.document, version=job.version,
                                     requested_by=job.requested_by, then=job.then)


# ---------------------------------------------------------------- natijadan keyin

def _notify(job, text, document=None):
    """So'rovchiga Telegram'da: matn va (bo'lsa) tayyor fayl."""
    user = job.requested_by
    if user is None or not user.telegram_chat_id:
        return
    from apps.telegram_bot.services import send_document, send_message

    send_message(user.telegram_chat_id, text, parse_mode=None)
    if document is not None and document.file and document.file_size <= 50 * 1024 * 1024:
        from apps.documents.archivist import open_file
        from apps.documents.services import file_basename

        with open_file(document) as fh:
            send_document(user.telegram_chat_id, fh, file_basename(document), document.name)


def _remarks_text(job):
    remarks = job.result.get("remarks") or []
    if not remarks:
        return f"✅ Нормоконтроль: {job.document.name} — замечаний нет."
    lines = [f"📋 Нормоконтроль: {job.document.name} — замечаний: {len(remarks)}"]
    for r in remarks[:30]:
        mark = "❗" if r.get("severity") == "critical" else "•"
        lines.append(f"{mark} {r.get('sheet', '')}: {r.get('issue', '')}")
        if r.get("issue_en"):
            lines.append(r["issue_en"])
    return "\n".join(lines)


def _after(job):
    if job.then == "secretary_review" and job.result_document is not None:
        from apps.ai_agents.secretary import request_approval

        request_approval(job.result_document, job.requested_by)
        return
    if job.kind == JobKind.NORM_CONTROL:
        _notify(job, _remarks_text(job)[:4000], job.result_document)
        return
    doc = job.result_document
    extra = job.result.get("summary") or ""
    _notify(job, f"✅ {job.get_kind_display()}: {doc.name if doc else job.document.name}" + (f"\n{extra}" if extra else ""), doc)
