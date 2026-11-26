from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Discipline, User
from apps.core.json_utils import script_json
from apps.notifications.services import notify_user
from apps.projects.models import Section, SubObject, SubObjectDiscipline
from apps.projects.permissions import can_edit_project, ensure_project_member, visible_projects_for

from .forms import (
    ApprovalReviewForm, ApprovalStageFormSet, ApprovalSubmissionForm, DocumentUploadForm, DocumentVersionForm,
)
from .models import ApprovalStage, ApprovalStatus, AuditLog, Document, DocumentStatus, DocumentVersion
from .services import build_zip, file_basename, zip_filename
from .services import resolve_gip_reviewer as _resolve_gip_reviewer
from .tasks import send_documents_to_telegram


def _visible_documents(user):
    return Document.objects.filter(project__in=visible_projects_for(user)).select_related("project", "uploaded_by")


def _can_modify(user, document):
    """O'chirish va yangi versiya — loyihada tahrir huquqi borlarga yoki
    hujjatni yuklaganning o'ziga. Ilgari loyihani faqat ko'ra oladigan har
    kim (mijoz roli ham) istalgan hujjatni o'chira olardi."""
    return document.uploaded_by_id == user.id or can_edit_project(user, document.project)


def _submission_cascade_json(projects):
    sub_objects = [
        {"id": str(so.pk), "project_id": str(so.project_id), "parent_id": str(so.parent_id) if so.parent_id else None,
         "name": so.name}
        for so in SubObject.objects.filter(project__in=projects)
    ]
    return script_json({"subObjects": sub_objects})


# Fayl turi filtri: kalit -> fayl nomi oxiri (regex).
FILE_KINDS = {
    "dwg": ("DWG", r"\.dwg$"),
    "pdf": ("PDF", r"\.pdf$"),
    "xls": ("Excel", r"\.xls[xm]?$"),
    "doc": ("Word", r"\.docx?$"),
}


def _filtered_documents(request):
    """Ro'yxat filtrlari (GET): loyiha, obyekt, intizom, fayl turi, holat,
    qidiruv. ZIP yuklash ham aynan shu natijani oladi."""
    documents = _visible_documents(request.user).select_related(
        "section__sub_object__parent", "section__discipline",
    )
    g = request.GET
    filters = {k: g.get(k, "") for k in ("project", "sub_object", "discipline", "kind", "status", "doc_type", "search")}
    if filters["project"]:
        documents = documents.filter(project_id=filters["project"])
    if filters["sub_object"]:
        # Obyekt tanlansa — uning pod-obyektlaridagi hujjatlar ham.
        documents = documents.filter(
            Q(section__sub_object_id=filters["sub_object"]) | Q(section__sub_object__parent_id=filters["sub_object"])
        )
    if filters["discipline"]:
        documents = documents.filter(section__discipline_id=filters["discipline"])
    if filters["kind"] in FILE_KINDS:
        documents = documents.filter(file__iregex=FILE_KINDS[filters["kind"]][1])
    if filters["status"]:
        documents = documents.filter(status=filters["status"])
    if filters["doc_type"]:
        documents = documents.filter(doc_type=filters["doc_type"])
    if filters["search"]:
        documents = documents.filter(name__icontains=filters["search"])
    return documents, filters


def _telegram_recipients():
    return (
        User.objects.filter(is_active=True).exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")
        .order_by("full_name")
    )


@login_required
def document_list(request):
    documents, filters = _filtered_documents(request)

    if request.method == "POST":
        ids = request.POST.getlist("selected")
        if "delete_selected" in request.POST and ids:
            selected = [
                document for document in _visible_documents(request.user).filter(pk__in=ids)
                if _can_modify(request.user, document)
            ]
            for document in selected:
                if document.file:
                    document.file.delete(save=False)
                document.delete()
            messages.success(request, _("Selected documents deleted."))
            return redirect("documents:list")
        if "send_telegram" in request.POST:
            recipient = _telegram_recipients().filter(pk=request.POST.get("recipient") or request.user.pk).first()
            count = _visible_documents(request.user).filter(pk__in=ids).exclude(file="").count() if ids else 0
            if not count:
                messages.error(request, _("Select documents with files to send."))
            elif recipient is None:
                messages.error(request, _("The recipient has not linked Telegram."))
            else:
                send_documents_to_telegram.delay(str(request.user.pk), str(recipient.pk), [str(i) for i in ids])
                messages.success(request, _("%(count)s file(s) are being sent to %(name)s in Telegram.") % {
                    "count": count, "name": recipient.get_short_name(),
                })
            return redirect(request.get_full_path())

    visible = _visible_documents(request.user)
    status_counts = {value: visible.filter(status=value).count() for value, _label in DocumentStatus.choices}

    paginator = Paginator(documents, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)

    sub_objects = SubObject.objects.none()
    if filters["project"]:
        sub_objects = SubObject.objects.filter(
            project_id=filters["project"], project__in=visible_projects_for(request.user),
        ).select_related("parent").order_by("parent__name", "name")

    return render(request, "documents/document_list.html", {
        "page_obj": page_obj,
        "status_counts": status_counts,
        "total": visible.count(),
        "filtered_total": paginator.count,
        "statuses": DocumentStatus.choices,
        "projects": visible_projects_for(request.user),
        "sub_objects": sub_objects,
        "disciplines": Discipline.objects.filter(sections__documents__in=visible).distinct(),
        "file_kinds": [(k, label) for k, (label, _rx) in FILE_KINDS.items()],
        "filters": filters,
        "querystring": query.urlencode(),
        "recipients": _telegram_recipients(),
    })


@login_required
def document_upload(request):
    if request.method == "POST":
        form = DocumentUploadForm(request.POST, request.FILES)
        form.fields["project"].queryset = visible_projects_for(request.user)
        if form.is_valid():
            document = form.save(commit=False)
            document.uploaded_by = request.user
            if document.file:
                document.file_size = document.file.size
                document.mime_type = getattr(document.file.file, "content_type", "")
            document.save()
            DocumentVersion.objects.create(
                document=document, version_number=document.version,
                file=document.file, file_size=document.file_size, uploaded_by=request.user,
            )
            AuditLog.log(obj=document, action="uploaded", user=request.user)
            messages.success(request, _("Document uploaded."))
            return redirect("documents:detail", pk=document.pk)
    else:
        form = DocumentUploadForm()
        form.fields["project"].queryset = visible_projects_for(request.user)
    return render(request, "documents/document_upload.html", {"form": form})


@login_required
def document_detail(request, pk):
    document = get_object_or_404(_visible_documents(request.user), pk=pk)
    show_audit = request.GET.get("audit") == "1"
    audit_entries = []
    if show_audit:
        audit_entries = AuditLog.objects.filter(
            content_type=ContentType.objects.get_for_model(Document), object_id=str(document.pk)
        )[:200]
    return render(request, "documents/document_detail.html", {
        "document": document,
        "show_audit": show_audit,
        "audit_entries": audit_entries,
        "version_form": DocumentVersionForm(),
        "can_modify": _can_modify(request.user, document),
        "can_assign_stages": can_edit_project(request.user, document.project),
    })


@login_required
def document_download(request, pk):
    document = get_object_or_404(_visible_documents(request.user), pk=pk)
    if not document.file:
        raise Http404
    try:
        file_handle = document.file.open("rb")
    except FileNotFoundError:
        raise Http404
    AuditLog.log(obj=document, action="downloaded", user=request.user)
    return FileResponse(file_handle, as_attachment=True, filename=file_basename(document))


@login_required
def document_version_download(request, pk):
    """Versiya faylini ham hujjatning ko'rinish qoidasi bo'yicha beradi —
    shablonlardagi to'g'ridan-to'g'ri ``version.file.url`` havolasi hech qanday
    tekshiruvdan o'tmasdi."""
    version = get_object_or_404(
        DocumentVersion.objects.select_related("document"),
        pk=pk, document__in=_visible_documents(request.user),
    )
    if not version.file:
        raise Http404
    try:
        file_handle = version.file.open("rb")
    except FileNotFoundError:
        raise Http404
    AuditLog.log(obj=version.document, action="version_downloaded", user=request.user)
    return FileResponse(file_handle, as_attachment=True, filename=file_basename(version))


@login_required
def document_bulk_download(request):
    """ZIP: ?id=... — tanlanganlar, ?all=1 — ro'yxat filtridagi hammasi.
    Arxiv ichida fayllar Loyiha/Obyekt/Intizom papkalarida."""
    if request.GET.get("all"):
        documents, _filters = _filtered_documents(request)
    else:
        documents = _visible_documents(request.user).filter(pk__in=request.GET.getlist("id")).select_related(
            "section__sub_object__parent", "section__discipline",
        )
    documents = list(documents)
    archive, added = build_zip(documents)
    for document in added:
        AuditLog.log(obj=document, action="bulk_download", user=request.user)
    return FileResponse(archive, as_attachment=True, filename=zip_filename(added or documents),
                        content_type="application/zip")


@login_required
def document_delete(request, pk):
    document = get_object_or_404(_visible_documents(request.user), pk=pk)
    if not _can_modify(request.user, document):
        raise PermissionDenied
    if request.method == "POST":
        if document.file:
            document.file.delete(save=False)
        document.delete()
        messages.success(request, _("Document deleted."))
        return redirect("documents:list")
    return render(request, "documents/document_confirm_delete.html", {"document": document})


@login_required
def document_add_version(request, pk):
    document = get_object_or_404(_visible_documents(request.user), pk=pk)
    if not _can_modify(request.user, document):
        raise PermissionDenied
    if request.method == "POST":
        form = DocumentVersionForm(request.POST, request.FILES)
        if form.is_valid():
            major = document.version.split(".")[0] if "." in document.version else document.version
            try:
                minor = int(document.version.split(".")[1]) + 1
            except (IndexError, ValueError):
                minor = 1
            new_version = f"{major}.{minor}"
            uploaded = form.cleaned_data["file"]
            DocumentVersion.objects.create(
                document=document, version_number=new_version, file=uploaded,
                file_size=uploaded.size, uploaded_by=request.user, notes=form.cleaned_data.get("notes"),
            )
            document.file = uploaded
            document.version = new_version
            document.file_size = uploaded.size
            document.save()
            AuditLog.log(obj=document, action="new_version", user=request.user, details={"version": new_version})
            messages.success(request, _("New version uploaded."))
    return redirect("documents:detail", pk=pk)


# --- Approval workflow ---------------------------------------------------

@login_required
def approval_submit(request):
    projects = visible_projects_for(request.user)
    if request.method == "POST":
        form = ApprovalSubmissionForm(request.POST, request.FILES, projects=projects)
        if form.is_valid():
            project = form.cleaned_data["project"]
            sub_object = form.cleaned_data["sub_object"]
            if sub_object.project_id != project.id:
                form.add_error("sub_object", _("The object must belong to the selected project."))
            else:
                discipline_assignment = SubObjectDiscipline.objects.filter(
                    sub_object=sub_object, discipline__in=request.user.disciplines.all(),
                ).select_related("discipline").first()
                if discipline_assignment is None:
                    form.add_error(
                        "sub_object",
                        _("You don't have a discipline assigned on this object, so it can't be submitted."),
                    )
                else:
                    reviewer = _resolve_gip_reviewer(sub_object, project)
                    if reviewer is None:
                        form.add_error(
                            "sub_object", _("This object has no GIP assigned to review submissions."),
                        )
                    else:
                        discipline = discipline_assignment.discipline
                        section = Section.objects.filter(
                            project=project, sub_object=sub_object, discipline=discipline,
                        ).first()
                        if section is None:
                            section = Section.objects.create(
                                project=project, sub_object=sub_object, discipline=discipline,
                                name=f"{discipline.code} — {sub_object.name}",
                            )
                        uploaded = form.cleaned_data["file"]
                        document = Document.objects.create(
                            name=form.cleaned_data["title"], project=project, section=section,
                            uploaded_by=request.user, file=uploaded, file_size=uploaded.size,
                            mime_type=getattr(uploaded, "content_type", "") or "",
                            status=DocumentStatus.REVIEW,
                        )
                        DocumentVersion.objects.create(
                            document=document, version_number=document.version, file=document.file,
                            file_size=document.file_size, uploaded_by=request.user,
                            notes=form.cleaned_data["comment"],
                        )
                        ApprovalStage.objects.create(
                            document=document, stage_order=1,
                            stage_name=f"{discipline.code} → GIP", reviewer=reviewer,
                        )
                        ensure_project_member(project, reviewer)
                        notify_user(
                            reviewer, "approval", _("New document to review"),
                            _("%(doc)s needs your review.") % {"doc": document.name},
                            link=f"/documents/{document.pk}/",
                        )
                        AuditLog.log(obj=document, action="uploaded", user=request.user)
                        messages.success(request, _("Sent for approval."))
                        return redirect("documents:approvals")
    else:
        form = ApprovalSubmissionForm(projects=projects)
    return render(request, "documents/approval_submit.html", {
        "form": form, "cascade_json": _submission_cascade_json(projects),
    })


@login_required
def approval_stage_assign(request, pk):
    document = get_object_or_404(_visible_documents(request.user), pk=pk)
    # Yuklovchining o'ziga ham ruxsat yo'q: aks holda o'zini tekshiruvchi
    # qilib tayinlab, o'z hujjatini o'zi tasdiqlab yuborardi.
    if not can_edit_project(request.user, document.project):
        raise PermissionDenied
    if request.method == "POST":
        formset = ApprovalStageFormSet(request.POST)
        if formset.is_valid():
            document.approval_stages.all().delete()
            order = 1
            for form in formset:
                if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                    continue
                stage = ApprovalStage.objects.create(
                    document=document, stage_order=order,
                    stage_name=form.cleaned_data["stage_name"],
                    reviewer=form.cleaned_data["reviewer"],
                )
                ensure_project_member(document.project, stage.reviewer)
                notify_user(
                    stage.reviewer, "approval", _("New document to review"),
                    _("%(doc)s needs your review.") % {"doc": document.name},
                    link=f"/documents/{document.pk}/",
                )
                order += 1
            document.status = DocumentStatus.REVIEW
            document.save(update_fields=["status", "updated_at"])
            messages.success(request, _("Approval route created."))
            return redirect("documents:detail", pk=pk)
    else:
        formset = ApprovalStageFormSet()
    return render(request, "documents/approval_stage_assign.html", {"document": document, "formset": formset})


@login_required
def approvals_list(request):
    tab = request.GET.get("tab", "pending")
    base = _visible_documents(request.user)
    if tab == "approved":
        documents = base.filter(status=DocumentStatus.APPROVED)
    elif tab == "rejected":
        documents = base.filter(status=DocumentStatus.REJECTED)
    else:
        documents = base.filter(status=DocumentStatus.REVIEW)

    stat_cards = [
        {"label": _("Awaiting approval"), "value": base.filter(status=DocumentStatus.REVIEW).count(),
         "color": "text-amber-600 dark:text-amber-400"},
        {"label": _("Approved"), "value": base.filter(status=DocumentStatus.APPROVED).count(),
         "color": "text-green-600 dark:text-green-400"},
        {"label": _("Rejected"), "value": base.filter(status=DocumentStatus.REJECTED).count(),
         "color": "text-red-600 dark:text-red-400"},
        {"label": _("My pending reviews"), "value": ApprovalStage.objects.filter(
            reviewer=request.user, status=ApprovalStatus.PENDING,
            document__in=base).count(),
         "color": "text-blue-600 dark:text-blue-400"},
    ]

    return render(request, "documents/approvals_list.html", {
        "documents": documents.prefetch_related("approval_stages__reviewer"),
        "tab": tab,
        "stat_cards": stat_cards,
    })


@login_required
def approval_stage_review(request, stage_id):
    stage = get_object_or_404(ApprovalStage, pk=stage_id)
    document = stage.document
    if document not in _visible_documents(request.user):
        raise PermissionDenied
    if stage.reviewer_id != request.user.id:
        raise PermissionDenied
    if stage.status != ApprovalStatus.PENDING:
        messages.error(request, _("This stage has already been reviewed."))
        return redirect("documents:detail", pk=document.pk)

    if request.method == "POST":
        form = ApprovalReviewForm(request.POST, request.FILES)
        if form.is_valid():
            new_status = form.cleaned_data["status"]
            stage.status = new_status
            stage.comment = form.cleaned_data["comment"]
            stage.response_file = form.cleaned_data.get("file") or None
            stage.reviewed_at = timezone.now()
            stage.save()

            if new_status == ApprovalStatus.REJECTED:
                document.status = DocumentStatus.REJECTED
            elif new_status == ApprovalStatus.REVISION:
                document.status = DocumentStatus.DRAFT
            elif new_status == ApprovalStatus.APPROVED:
                remaining = document.approval_stages.exclude(pk=stage.pk).exclude(status=ApprovalStatus.APPROVED)
                if not remaining.exists():
                    document.status = DocumentStatus.APPROVED
                    if document.section_id and document.section.sub_object_id:
                        SubObjectDiscipline.objects.update_or_create(
                            sub_object_id=document.section.sub_object_id,
                            discipline_id=document.section.discipline_id,
                            defaults={"progress": 100},
                        )
            document.save(update_fields=["status", "updated_at"])

            if document.source_task_id:
                from apps.tasks.models import Task, TaskComment

                task = document.source_task
                if new_status in (ApprovalStatus.REJECTED, ApprovalStatus.REVISION):
                    task.status = Task.Status.REVISION
                    task.save(update_fields=["status", "updated_at"])
                    TaskComment.objects.create(
                        task=task, user=request.user,
                        content=stage.comment or _("Sent back for revision from the Approvals section."),
                    )
                    if task.assignee and task.assignee_id != request.user.id:
                        notify_user(
                            task.assignee, "task", _("Task sent back for revision"),
                            _('"%(title)s" needs revision — see the approval comment.') % {"title": task.title},
                            link=f"/tasks/{task.pk}/",
                        )
                elif document.status == DocumentStatus.APPROVED:
                    # The GIP signed it off, so the task itself is approved.
                    task.status = Task.Status.APPROVED
                    task.save(update_fields=["status", "updated_at"])
                    if task.assignee and task.assignee_id != request.user.id:
                        notify_user(
                            task.assignee, "task", _("Task approved"),
                            _('"%(title)s" was approved by the GIP.') % {"title": task.title},
                            link=f"/tasks/{task.pk}/",
                        )

            AuditLog.log(obj=document, action=f"approval_{new_status}", user=request.user)
            notify_user(
                document.uploaded_by, "approval", _("Document review update"),
                _("%(doc)s was marked as %(status)s.") % {"doc": document.name, "status": new_status},
                link=f"/documents/{document.pk}/",
            )
            messages.success(request, _("Review submitted."))
            return redirect("documents:approvals")
    else:
        form = ApprovalReviewForm()
    return render(request, "documents/approval_stage_review.html", {"stage": stage, "document": document, "form": form})
