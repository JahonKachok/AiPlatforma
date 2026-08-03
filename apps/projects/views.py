import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.documents.models import AuditLog, Document, DocumentVersion
from apps.finance.forms import FinancialRecordForm
from apps.tasks.forms import SubObjectTaskForm, TaskChecklistItemForm
from apps.tasks.models import Task, TaskChecklistItem

from .forms import (
    ProjectClientForm, ProjectForm, ProjectMemberForm, ProjectWizardDocumentForm,
    SectionForm, SubObjectForm, SubObjectWorkerForm,
)
from .models import Project, ProjectMember, SubObject, SubObjectWorker
from .permissions import can_create_project, can_edit_project, visible_projects_for
from .uz_regions import REGION_CENTERS

WIZARD_DOC_TYPES = [
    ("project_doc", _("Project document")),
    ("estimate", _("Estimate")),
    ("technical_task", _("Technical assignment")),
    ("permit", _("Permit")),
]

REGION_CENTERS_JSON = json.dumps(REGION_CENTERS)

TRACKED_FIELDS = [
    "name", "description", "client_name", "client_contact", "region", "district", "address",
    "stage", "status", "start_date", "deadline", "budget", "paid_amount",
]


@login_required
def project_list(request):
    visible = visible_projects_for(request.user)
    projects = visible

    status = request.GET.get("status")
    if status:
        projects = projects.filter(status=status)
    search = request.GET.get("search")
    if search:
        projects = projects.filter(name__icontains=search)

    paginator = Paginator(projects, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    today = date.today()
    stat_cards = [
        {"label": _("Total"), "value": visible.count()},
        {"label": _("Active"), "value": visible.filter(status=Project.Status.ACTIVE).count(),
         "color": "text-blue-600 dark:text-blue-400"},
        {"label": _("Completed"), "value": visible.filter(status=Project.Status.COMPLETED).count(),
         "color": "text-green-600 dark:text-green-400"},
        {"label": _("Deadline passed"), "value": visible.filter(
            status=Project.Status.ACTIVE, deadline__lt=today).count(),
         "color": "text-red-600 dark:text-red-400"},
    ]

    return render(request, "projects/project_list.html", {
        "page_obj": page_obj,
        "status": status or "",
        "search": search or "",
        "statuses": Project.Status.choices,
        "can_create": can_create_project(request.user),
        "stat_cards": stat_cards,
    })


@login_required
def project_create(request):
    if not can_create_project(request.user):
        raise PermissionDenied
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            ProjectMember.objects.get_or_create(
                project=project, user=request.user, defaults={"role_in_project": "owner"}
            )
            gip = form.cleaned_data.get("gip")
            if gip:
                ProjectMember.objects.update_or_create(
                    project=project, user=gip, defaults={"role_in_project": "gip"}
                )
            AuditLog.log(obj=project, action="created", user=request.user)
            messages.success(request, _("Project created."))
            return redirect("projects:wizard_subobjects", pk=project.pk)
    else:
        form = ProjectForm()
    return render(request, "projects/project_form.html", {
        "form": form, "is_create": True, "region_centers_json": REGION_CENTERS_JSON,
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects.prefetch_related(
            "members__user", "sub_objects__sections__discipline", "sections__discipline",
        ),
        pk=pk,
    )
    if project not in visible_projects_for(request.user):
        raise PermissionDenied

    orphan_sections = [section for section in project.sections.all() if not section.sub_object_id]

    discipline_ids = {section.discipline_id for section in project.sections.all()}
    employees_by_discipline = {}
    if discipline_ids:
        qualified_users = User.objects.filter(
            disciplines__in=discipline_ids, is_active=True,
        ).distinct().prefetch_related("disciplines")
        for user in qualified_users:
            for discipline in user.disciplines.all():
                if discipline.id in discipline_ids:
                    employees_by_discipline.setdefault(discipline.id, []).append(user)

    for sub_object in project.sub_objects.all():
        for section in sub_object.sections.all():
            section.qualified_employees = employees_by_discipline.get(section.discipline_id, [])
    for section in orphan_sections:
        section.qualified_employees = employees_by_discipline.get(section.discipline_id, [])

    tasks = project.tasks.select_related("assignee")[:6]
    task_stats = {
        "total": project.tasks.count(),
        "completed": project.tasks.filter(status=Task.Status.COMPLETED).count(),
        "in_progress": project.tasks.filter(status=Task.Status.IN_PROGRESS).count(),
    }
    records = project.financial_records.all()[:20]
    income = sum(r.amount for r in project.financial_records.filter(type="income"))
    expense = sum(r.amount for r in project.financial_records.filter(type="expense"))

    return render(request, "projects/project_detail.html", {
        "project": project,
        "tasks": tasks,
        "task_stats": task_stats,
        "records": records,
        "income": income,
        "expense": expense,
        "can_edit": can_edit_project(request.user, project),
        "orphan_sections": orphan_sections,
        "sub_object_form": SubObjectForm(),
        "section_form": SectionForm(project=project),
        "member_form": ProjectMemberForm(),
        "record_form": FinancialRecordForm(),
    })


@login_required
def project_update(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied

    before = {f: getattr(project, f) for f in TRACKED_FIELDS}
    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            after = {f: getattr(project, f) for f in TRACKED_FIELDS}
            changes = {f: [str(before[f]), str(after[f])] for f in TRACKED_FIELDS if before[f] != after[f]}
            if changes:
                AuditLog.log(obj=project, action="updated", user=request.user, details=changes)
            messages.success(request, _("Project updated."))
            return redirect("projects:detail", pk=project.pk)
    else:
        form = ProjectForm(instance=project)
    return render(request, "projects/project_form.html", {
        "form": form, "project": project, "is_create": False, "region_centers_json": REGION_CENTERS_JSON,
        "client_form": ProjectClientForm(instance=project),
    })


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        AuditLog.log(obj=project, action="deleted", user=request.user)
        project.delete()
        messages.success(request, _("Project deleted."))
        return redirect("projects:list")
    return render(request, "projects/project_confirm_delete.html", {"project": project})


@login_required
def project_history(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project not in visible_projects_for(request.user):
        raise PermissionDenied
    from django.contrib.contenttypes.models import ContentType
    entries = AuditLog.objects.filter(
        content_type=ContentType.objects.get_for_model(Project), object_id=str(project.pk)
    )[:200]
    return render(request, "projects/project_history.html", {"project": project, "entries": entries})


@login_required
def project_add_member(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = ProjectMemberForm(request.POST)
        if form.is_valid():
            member = form.save(commit=False)
            member.project = project
            if not ProjectMember.objects.filter(project=project, user=member.user).exists():
                member.save()
                messages.success(request, _("Member added."))
            else:
                messages.error(request, _("This user is already a member."))
    return redirect("projects:detail", pk=pk)


@login_required
def project_remove_member(request, pk, user_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    ProjectMember.objects.filter(project=project, user_id=user_id).delete()
    messages.success(request, _("Member removed."))
    return redirect("projects:detail", pk=pk)


@login_required
def project_add_subobject(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = SubObjectForm(request.POST)
        if form.is_valid():
            sub_object = form.save(commit=False)
            sub_object.project = project
            sub_object.save()
            messages.success(request, _("Sub-object added."))
    return redirect("projects:detail", pk=pk)


@login_required
def project_add_section(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = SectionForm(request.POST, project=project)
        if form.is_valid():
            section = form.save(commit=False)
            section.project = project
            section.save()
            messages.success(request, _("Section added."))
    return redirect("projects:detail", pk=pk)


def _subobjects_queryset(project):
    return project.sub_objects.prefetch_related(
        "workers__user", "tasks__assignee", "tasks__checklist_items",
    )


def _render_subobject_card(request, sub_object, has_error=False):
    return render_to_string("projects/_wizard_subobject_card.html", {
        "sub": sub_object, "has_error": has_error, "form": SubObjectForm(instance=sub_object),
    }, request=request)


def _render_task_item(request, task):
    return render_to_string("projects/_wizard_task_item.html", {
        "task": task, "form": SubObjectTaskForm(instance=task),
    }, request=request)


@login_required
def project_wizard_subobjects(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied

    if request.method == "POST":
        sub_objects = list(_subobjects_queryset(project))
        errors = []
        error_ids = set()
        if not sub_objects:
            errors.append(_("Add at least one sub-object."))
        for sub in sub_objects:
            problems = []
            if not sub.name:
                problems.append(_("Name is required."))
            if not sub.deadline:
                problems.append(_("Deadline is required."))
            if not sub.workers.exists():
                problems.append(_("At least one worker must be assigned."))
            if not sub.tasks.exists():
                problems.append(_("At least one task is required."))
            if problems:
                error_ids.add(sub.id)
                errors.append(f"{sub.name or _('(unnamed)')}: " + " ".join(str(p) for p in problems))
        if errors:
            for message in errors:
                messages.error(request, message)
            for sub in sub_objects:
                sub.has_error = sub.id in error_ids
            return render(request, "projects/project_wizard_subobjects.html", {
                "project": project, "sub_objects": sub_objects,
            })
        return redirect("projects:wizard_documents", pk=pk)

    sub_objects = list(_subobjects_queryset(project))
    for sub in sub_objects:
        sub.has_error = False
    return render(request, "projects/project_wizard_subobjects.html", {
        "project": project, "sub_objects": sub_objects,
    })


@login_required
def wizard_subobject_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    max_position = SubObject.objects.filter(project=project).count()
    sub_object = SubObject.objects.create(
        project=project, name=str(_("New sub-object")), position=max_position,
    )
    return JsonResponse({"id": str(sub_object.pk), "html": _render_subobject_card(request, sub_object)})


@login_required
def wizard_subobject_update(request, pk, sub_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    sub_object = get_object_or_404(SubObject, pk=sub_id, project=project)
    form = SubObjectForm(request.POST, instance=sub_object)
    form.fields["deadline"].required = False
    if not form.is_valid():
        return JsonResponse({"error": form.errors.as_text()}, status=400)
    form.save()
    return JsonResponse({
        "ok": True,
        "progress": sub_object.progress_percentage,
        "days_remaining": sub_object.days_remaining,
    })


@login_required
def wizard_subobject_delete(request, pk, sub_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    SubObject.objects.filter(pk=sub_id, project=project).delete()
    return JsonResponse({"ok": True})


@login_required
def wizard_subobject_duplicate(request, pk, sub_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    original = get_object_or_404(SubObject, pk=sub_id, project=project)
    max_position = SubObject.objects.filter(project=project).count()
    copy = SubObject.objects.create(
        project=project, name=f"{original.name} ({_('copy')})", description=original.description,
        priority=original.priority, status=original.status, start_date=original.start_date,
        deadline=original.deadline, gip=original.gip, position=max_position,
    )
    for worker in original.workers.all():
        SubObjectWorker.objects.create(
            sub_object=copy, user=worker.user, role=worker.role,
            deadline=worker.deadline, status=worker.status,
        )
    for task in original.tasks.all():
        task_copy = Task.objects.create(
            project=project, sub_object=copy, title=task.title, description=task.description,
            assignee=task.assignee, creator=request.user, status=task.status,
            priority=task.priority, deadline=task.deadline, position=task.position,
        )
        for item in task.checklist_items.all():
            TaskChecklistItem.objects.create(
                task=task_copy, text=item.text, is_done=item.is_done, position=item.position,
            )
    return JsonResponse({"id": str(copy.pk), "html": _render_subobject_card(request, copy)})


@login_required
def wizard_subobject_reorder(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    ids = request.POST.getlist("order[]") or request.POST.getlist("order")
    for index, sub_id in enumerate(ids):
        SubObject.objects.filter(pk=sub_id, project=project).update(position=index)
    return JsonResponse({"ok": True})


@login_required
def wizard_worker_search(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    query = request.GET.get("q", "").strip()
    sub_id = request.GET.get("sub_object")
    users = User.objects.filter(is_active=True)
    if query:
        users = users.filter(full_name__icontains=query)
    if sub_id:
        users = users.exclude(sub_object_assignments__sub_object_id=sub_id)
    users = users.select_related()[:20]
    return JsonResponse({
        "results": [
            {"id": str(u.pk), "label": f"{u.full_name} — {u.get_role_display()}"}
            for u in users
        ],
    })


@login_required
def wizard_worker_add(request, pk, sub_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    sub_object = get_object_or_404(SubObject, pk=sub_id, project=project)
    form = SubObjectWorkerForm(request.POST, sub_object=sub_object)
    if not form.is_valid():
        return JsonResponse({"error": form.errors.as_text()}, status=400)
    worker = form.save(commit=False)
    worker.sub_object = sub_object
    worker.save()
    html = render_to_string("projects/_wizard_worker_chip.html", {"worker": worker}, request=request)
    return JsonResponse({"id": str(worker.pk), "html": html})


@login_required
def wizard_worker_remove(request, pk, sub_id, worker_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    SubObjectWorker.objects.filter(pk=worker_id, sub_object_id=sub_id, sub_object__project=project).delete()
    return JsonResponse({"ok": True})


@login_required
def wizard_task_create(request, pk, sub_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    sub_object = get_object_or_404(SubObject, pk=sub_id, project=project)
    task = Task.objects.create(
        project=project, sub_object=sub_object, creator=request.user,
        title=str(_("New task")), position=sub_object.tasks.count(),
    )
    html = _render_task_item(request, task)
    return JsonResponse({
        "id": str(task.pk), "html": html, "progress": sub_object.progress_percentage,
    })


@login_required
def wizard_task_update(request, pk, task_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    task = get_object_or_404(Task, pk=task_id, project=project)
    form = SubObjectTaskForm(request.POST, instance=task)
    if not form.is_valid():
        return JsonResponse({"error": form.errors.as_text()}, status=400)
    form.save()
    progress = task.sub_object.progress_percentage if task.sub_object_id else None
    return JsonResponse({"ok": True, "progress": progress})


@login_required
def wizard_task_delete(request, pk, task_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    task = get_object_or_404(Task, pk=task_id, project=project)
    sub_object = task.sub_object
    task.delete()
    return JsonResponse({
        "ok": True, "progress": sub_object.progress_percentage if sub_object else None,
    })


@login_required
def wizard_task_reorder(request, pk, sub_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    ids = request.POST.getlist("order[]") or request.POST.getlist("order")
    for index, task_id in enumerate(ids):
        Task.objects.filter(pk=task_id, sub_object_id=sub_id, project=project).update(position=index)
    return JsonResponse({"ok": True})


@login_required
def wizard_checklist_add(request, pk, task_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    task = get_object_or_404(Task, pk=task_id, project=project)
    form = TaskChecklistItemForm(request.POST)
    if not form.is_valid():
        return JsonResponse({"error": form.errors.as_text()}, status=400)
    item = form.save(commit=False)
    item.task = task
    item.position = task.checklist_items.count()
    item.save()
    html = render_to_string("projects/_wizard_checklist_item.html", {"item": item}, request=request)
    return JsonResponse({"id": str(item.pk), "html": html})


@login_required
def wizard_checklist_toggle(request, pk, item_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    item = get_object_or_404(TaskChecklistItem, pk=item_id, task__project=project)
    item.is_done = not item.is_done
    item.save(update_fields=["is_done"])
    return JsonResponse({"ok": True, "is_done": item.is_done})


@login_required
def wizard_checklist_delete(request, pk, item_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    TaskChecklistItem.objects.filter(pk=item_id, task__project=project).delete()
    return JsonResponse({"ok": True})


@login_required
def project_update_client(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method == "POST":
        form = ProjectClientForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, _("Client information updated."))
    return redirect("projects:update", pk=pk)


@login_required
def project_wizard_documents(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    doc_type_keys = [key for key, _label in WIZARD_DOC_TYPES]
    documents = {
        doc.doc_type: doc
        for doc in Document.objects.filter(project=project, doc_type__in=doc_type_keys)
    }
    checklist = [
        {"key": key, "label": label, "document": documents.get(key)}
        for key, label in WIZARD_DOC_TYPES
    ]
    return render(request, "projects/project_wizard_documents.html", {
        "project": project, "checklist": checklist,
    })


@login_required
def project_wizard_document_upload(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method != "POST":
        raise PermissionDenied
    doc_type = request.POST.get("doc_type")
    if doc_type not in [key for key, _label in WIZARD_DOC_TYPES]:
        return JsonResponse({"error": _("Unknown document type.")}, status=400)
    form = ProjectWizardDocumentForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"error": " ".join(form.errors.get("file", []))}, status=400)

    uploaded = form.cleaned_data["file"]
    Document.objects.filter(project=project, doc_type=doc_type).delete()
    document = Document.objects.create(
        project=project, uploaded_by=request.user, doc_type=doc_type,
        name=uploaded.name, file=uploaded, file_size=uploaded.size,
        mime_type=getattr(uploaded, "content_type", "") or "",
    )
    DocumentVersion.objects.create(
        document=document, version_number=document.version,
        file=document.file, file_size=document.file_size, uploaded_by=request.user,
    )
    AuditLog.log(obj=document, action="uploaded", user=request.user)
    return JsonResponse({"id": str(document.pk), "name": document.name})


@login_required
def project_wizard_document_delete(request, pk, doc_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    if request.method != "POST":
        raise PermissionDenied
    document = get_object_or_404(Document, pk=doc_id, project=project)
    if document.file:
        document.file.delete(save=False)
    document.delete()
    return JsonResponse({"ok": True})


@login_required
def project_wizard_confirm(request, pk):
    project = get_object_or_404(
        Project.objects.prefetch_related("sub_objects__sections__discipline"), pk=pk,
    )
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    doc_type_keys = [key for key, _label in WIZARD_DOC_TYPES]
    documents = Document.objects.filter(project=project, doc_type__in=doc_type_keys)
    if request.method == "POST":
        AuditLog.log(obj=project, action="wizard_completed", user=request.user)
        messages.success(request, _("Project created."))
        return redirect("projects:detail", pk=pk)
    return render(request, "projects/project_wizard_confirm.html", {
        "project": project, "documents": documents,
    })
