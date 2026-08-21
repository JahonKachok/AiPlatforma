from django.utils.translation import gettext_lazy as _

from apps.documents.models import ApprovalStage, AuditLog, Document, DocumentStatus
from apps.documents.services import resolve_gip_reviewer
from apps.notifications.services import notify_user
from apps.projects.permissions import ensure_project_member

from .permissions import resolve_reviewer


def submit_task_for_approval(task, actor):
    """Called when a task's reviewer (GIP) approves it (review -> approved).
    Creates/refreshes the linked Document + a pending ApprovalStage so the
    task's output surfaces in the Approvals 'awaiting approval' list.
    Returns the Document, or None if the task has no discipline/GIP to route to."""
    if not (task.section_id and task.section.sub_object_id):
        return None
    sub_object = task.section.sub_object
    reviewer = resolve_reviewer(task) or resolve_gip_reviewer(sub_object, task.project)
    if reviewer is None:
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
        document.save(update_fields=["status", "updated_at"])

    attachment = task.attachments.first()  # TaskAttachment.Meta.ordering = ["-created_at"]
    if attachment:
        document.file = attachment.file
        document.file_size = attachment.file_size
        document.mime_type = attachment.mime_type or ""
        document.save(update_fields=["file", "file_size", "mime_type", "updated_at"])

    stage_order = document.approval_stages.count() + 1
    ApprovalStage.objects.create(
        document=document, stage_order=stage_order,
        stage_name=f"{task.section.discipline.code} → GIP", reviewer=reviewer,
    )
    ensure_project_member(task.project, reviewer)
    notify_user(
        reviewer, "approval", _("New document to review"),
        _("%(doc)s needs your review.") % {"doc": document.name},
        link=f"/documents/{document.pk}/",
    )
    AuditLog.log(obj=document, action="uploaded", user=actor)
    return document
