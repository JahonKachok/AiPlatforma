from django.utils.translation import gettext_lazy as _

from apps.documents.models import ApprovalStage, AuditLog, Document, DocumentStatus
from apps.documents.services import resolve_gip_reviewer, resolve_project_gip
from apps.notifications.services import notify_user
from apps.projects.permissions import ensure_project_member


def resolve_approver(task):
    """Who signs the task off: the GIP attached to the project, falling back to
    the GIP of the task's own object when the project has none."""
    approver = resolve_project_gip(task.project)
    if approver is not None:
        return approver
    sub_object = task.section.sub_object if task.section_id else None
    return resolve_gip_reviewer(sub_object, task.project)


def submit_task_for_approval(task, actor):
    """Send a checked task to the project's GIP for sign-off: creates (or
    refreshes) the linked Document plus a pending ApprovalStage, so it shows up
    in the Approvals 'awaiting approval' list. The task only becomes approved
    once the GIP actually approves it there.

    Returns the Document, or None when the project has no GIP to send it to."""
    approver = resolve_approver(task)
    if approver is None:
        return None

    document, created = Document.objects.get_or_create(
        source_task=task,
        defaults={
            "name": task.title, "project": task.project, "section": task.section,
            "uploaded_by": task.assignee or actor, "status": DocumentStatus.REVIEW,
        },
    )
    if not created:
        document.status = DocumentStatus.REVIEW
        document.section = task.section
        document.save(update_fields=["status", "section", "updated_at"])

    attachment = task.attachments.first()  # TaskAttachment.Meta.ordering = ["-created_at"]
    if attachment:
        document.file = attachment.file
        document.file_size = attachment.file_size
        document.mime_type = attachment.mime_type or ""
        document.save(update_fields=["file", "file_size", "mime_type", "updated_at"])

    discipline = task.section.discipline.code if task.section_id else task.project.name
    stage_order = document.approval_stages.count() + 1
    ApprovalStage.objects.create(
        document=document, stage_order=stage_order,
        stage_name=f"{discipline} → GIP", reviewer=approver,
    )
    ensure_project_member(task.project, approver)
    notify_user(
        approver, "approval", _("New document to review"),
        _("%(doc)s needs your review.") % {"doc": document.name},
        link=f"/documents/{document.pk}/",
    )
    AuditLog.log(obj=document, action="uploaded", user=actor)
    return document
