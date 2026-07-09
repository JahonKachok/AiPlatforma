import io
import zipfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.notifications.services import notify_user
from apps.projects.permissions import ensure_project_member, visible_projects_for

from .forms import ApprovalReviewForm, ApprovalStageFormSet, DocumentUploadForm, DocumentVersionForm
from .models import ApprovalStage, ApprovalStatus, AuditLog, Document, DocumentStatus, DocumentVersion


def _visible_documents(user):
    return Document.objects.filter(project__in=visible_projects_for(user)).select_related("project", "uploaded_by")


@login_required
def document_list(request):
    documents = _visible_documents(request.user)

    project_id = request.GET.get("project")
    if project_id:
        documents = documents.filter(project_id=project_id)
    status = request.GET.get("status")
    if status:
        documents = documents.filter(status=status)
    doc_type = request.GET.get("doc_type")
    if doc_type:
        documents = documents.filter(doc_type=doc_type)
    search = request.GET.get("search")
    if search:
        documents = documents.filter(name__icontains=search)

    if request.method == "POST":
        ids = request.POST.getlist("selected")
        if "delete_selected" in request.POST and ids:
            _visible_documents(request.user).filter(pk__in=ids).delete()
            messages.success(request, _("Selected documents deleted."))
            return redirect("documents:list")

    status_counts = {
        value: _visible_documents(request.user).filter(status=value).count()
        for value, _label in DocumentStatus.choices
    }

    paginator = Paginator(documents, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "documents/document_list.html", {
        "page_obj": page_obj,
        "status_counts": status_counts,
        "total": _visible_documents(request.user).count(),
        "statuses": DocumentStatus.choices,
        "projects": visible_projects_for(request.user),
        "filters": {
            "project": project_id or "", "status": status or "",
            "doc_type": doc_type or "", "search": search or "",
        },
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
    })


@login_required
def document_download(request, pk):
    document = get_object_or_404(_visible_documents(request.user), pk=pk)
    if not document.file:
        raise Http404
    AuditLog.log(obj=document, action="downloaded", user=request.user)
    return FileResponse(document.file.open("rb"), as_attachment=True, filename=document.file.name.split("/")[-1])


@login_required
def document_bulk_download(request):
    ids = request.GET.getlist("id")
    documents = _visible_documents(request.user).filter(pk__in=ids)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for document in documents:
            if document.file:
                zf.writestr(document.file.name.split("/")[-1], document.file.read())
                AuditLog.log(obj=document, action="bulk_download", user=request.user)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = 'attachment; filename="documents.zip"'
    return response


@login_required
def document_delete(request, pk):
    document = get_object_or_404(_visible_documents(request.user), pk=pk)
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


@login_required
def document_quick_approve(request, pk):
    document = get_object_or_404(_visible_documents(request.user), pk=pk)
    if request.method == "POST" and document.status == DocumentStatus.DRAFT:
        document.status = DocumentStatus.APPROVED
        document.save(update_fields=["status", "updated_at"])
        AuditLog.log(obj=document, action="quick_approved", user=request.user)
    return redirect("documents:list")


# --- Approval workflow ---------------------------------------------------

@login_required
def approval_stage_assign(request, pk):
    document = get_object_or_404(_visible_documents(request.user), pk=pk)
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
        form = ApprovalReviewForm(request.POST)
        if form.is_valid():
            new_status = form.cleaned_data["status"]
            stage.status = new_status
            stage.comment = form.cleaned_data.get("comment")
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
            document.save(update_fields=["status", "updated_at"])

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
