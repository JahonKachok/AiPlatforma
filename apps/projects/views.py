import io
import json
import zipfile
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Discipline, User
from apps.documents.models import AuditLog, Document, DocumentVersion
from apps.finance.forms import FinancialRecordForm
from apps.notifications.models import NotificationType
from apps.notifications.services import notify_user
from apps.tasks.models import Task

from .excel_import import InvalidExcelStructureError, build_subobjects_import_template, import_subobjects_from_excel
from .forms import (
    ProjectClientForm, ProjectForm, ProjectMemberForm, ProjectWizardDocumentForm,
    SectionForm, SubObjectDisciplineForm, SubObjectForm,
)
from .models import Project, ProjectMember, SubObject, SubObjectDiscipline
from .permissions import can_create_project, can_edit_project, visible_projects_for
from .uz_regions import REGION_CENTERS

WIZARD_DOC_TYPES = [
    ("tz", _("10_ТЗ")),
    ("geology", _("20_Геология")),
    ("ecology", _("30_Экология")),
    ("cadastre", _("40_Кадастр")),
    ("apz", _("50_АПЗ")),
    ("tu", _("60_ТУ")),
    ("kd_equipment", _("70_КД оборудования")),
    ("photo_video", _("80_Фото и видео")),
]


def _wizard_discipline_query(sub_object):
    """GET query string that re-selects a sub-object (and its parent, if it's a pod object)
    on the wizard disciplines step after a redirect."""
    if sub_object.parent_id:
        return f"sub_object={sub_object.parent_id}&pod_object={sub_object.pk}"
    return f"sub_object={sub_object.pk}"


def _apply_discipline_weight_updates(sub_object, post_data):
    """Parse weight_<pk>/progress_<pk> fields for sub_object's disciplines out of post_data
    and persist them. Weight is required for an assignment to be touched; progress is only
    updated when the caller actually posts a progress_<pk> field for it (the project-setup
    wizard only collects weights — progress is tracked later, once work is underway).
    Returns an error message on failure (nothing is saved), or None on success. A no-op if
    post_data carries no weight fields for this sub_object at all (e.g. the wizard's
    "continue" button was submitted with no object selected)."""
    assignments = list(SubObjectDiscipline.objects.filter(sub_object=sub_object))
    if not assignments or not any(f"weight_{a.pk}" in post_data for a in assignments):
        return None

    updates = []
    for assignment in assignments:
        raw_weight = post_data.get(f"weight_{assignment.pk}")
        if raw_weight is None:
            continue
        try:
            weight = int(raw_weight)
        except (TypeError, ValueError):
            return _("Weight must be a whole number.")
        if not (0 <= weight <= 100):
            return _("Weight must be between 0 and 100.")
        assignment.weight = weight

        raw_progress = post_data.get(f"progress_{assignment.pk}")
        if raw_progress is not None:
            try:
                progress = int(raw_progress)
            except (TypeError, ValueError):
                return _("Progress must be a whole number.")
            if not (0 <= progress <= 100):
                return _("Progress must be between 0 and 100.")
            assignment.progress = progress

        updates.append(assignment)

    if updates:
        SubObjectDiscipline.objects.bulk_update(updates, ["weight", "progress"])
    return None


def _next_or(request, project, fallback_url):
    """Actions on the structure tab (project_detail) submit next=detail so they land back
    on that tab instead of the wizard page these views were originally written for."""
    if request.POST.get("next") == "detail":
        return reverse("projects:detail", args=[project.pk]) + "#tab-structure"
    return fallback_url

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
            "sub_objects__pod_objects__disciplines__discipline",
            "sub_objects__pod_objects__disciplines__assignee",
            "sub_objects__disciplines__discipline",
            "sub_objects__disciplines__assignee",
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

    # Objects & sub-objects tab: a SubObject with parent=None is an "Object" (Объект),
    # one with a parent is a "Pod object" (Подобъект) — build the object -> pod-object tree here
    # instead of listing all SubObjects flat, and work out which disciplines each leaf node
    # (a pod object, or an object with no pod objects) can still have added.
    all_disciplines = list(Discipline.objects.all().order_by("code"))
    top_objects = [obj for obj in project.sub_objects.all() if obj.parent_id is None]

    def _attach_available_disciplines(target):
        assigned_ids = {d.discipline_id for d in target.disciplines.all()}
        target.available_disciplines = [d for d in all_disciplines if d.id not in assigned_ids]

    for obj in top_objects:
        _attach_available_disciplines(obj)
        for pod in obj.pod_objects.all():
            _attach_available_disciplines(pod)

    # Maps discipline id -> list of active users with that discipline, used client-side to
    # populate the "assignee" dropdown once a discipline is picked for a pod/object.
    discipline_users = {}
    for user in User.objects.filter(is_active=True).prefetch_related("disciplines"):
        for discipline in user.disciplines.all():
            discipline_users.setdefault(str(discipline.id), []).append(
                {"id": str(user.id), "name": user.full_name or user.email}
            )

    tasks = project.tasks.select_related("assignee")[:6]
    task_stats = {
        "total": project.tasks.count(),
        "completed": project.tasks.filter(status=Task.Status.COMPLETED).count(),
        "in_progress": project.tasks.filter(status=Task.Status.IN_PROGRESS).count(),
    }
    records = project.financial_records.all()[:20]
    income = sum(r.amount for r in project.financial_records.filter(type="income"))
    expense = sum(r.amount for r in project.financial_records.filter(type="expense"))

    doc_type_keys = [key for key, _label in WIZARD_DOC_TYPES]
    documents_by_type = {}
    for doc in Document.objects.filter(project=project, doc_type__in=doc_type_keys).order_by("-created_at"):
        documents_by_type.setdefault(doc.doc_type, []).append(doc)
    source_files_checklist = [
        {"key": key, "label": label, "documents": documents_by_type.get(key, [])}
        for key, label in WIZARD_DOC_TYPES
    ]

    return render(request, "projects/project_detail.html", {
        "project": project,
        "tasks": tasks,
        "task_stats": task_stats,
        "records": records,
        "income": income,
        "expense": expense,
        "can_edit": can_edit_project(request.user, project),
        "orphan_sections": orphan_sections,
        "top_objects": top_objects,
        "discipline_users": discipline_users,
        "sub_object_form": SubObjectForm(),
        "section_form": SectionForm(project=project),
        "member_form": ProjectMemberForm(),
        "record_form": FinancialRecordForm(),
        "source_files_checklist": source_files_checklist,
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
            return redirect("projects:wizard_subobjects", pk=project.pk)
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


@login_required
def project_wizard_subobjects(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied

    if request.method == "POST":
        messages.success(request, _("Project structure saved."))
        return redirect("projects:wizard_disciplines", pk=pk)

    sub_objects = list(project.sub_objects.filter(parent__isnull=True))
    selected_id = request.GET.get("sub_object") or (str(sub_objects[0].pk) if sub_objects else None)
    selected = next((s for s in sub_objects if str(s.pk) == str(selected_id)), None) if selected_id else None

    pod_objects = []
    if selected:
        pod_objects = list(selected.pod_objects.all())

    return render(request, "projects/project_wizard_subobjects.html", {
        "project": project, "sub_objects": sub_objects, "selected": selected,
        "pod_objects": pod_objects,
    })


@login_required
def project_wizard_disciplines(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied

    if request.method == "POST":
        target_id = request.POST.get("target_id")
        if target_id:
            target = get_object_or_404(SubObject, pk=target_id, project=project)
            error = _apply_discipline_weight_updates(target, request.POST)
            if error:
                messages.error(request, error)
                base_url = reverse("projects:wizard_disciplines", args=[pk])
                query = _wizard_discipline_query(target)
                return redirect(f"{base_url}?{query}")

        assignments = SubObjectDiscipline.objects.filter(
            sub_object__project=project, assignee__isnull=False,
        ).select_related("assignee", "discipline", "sub_object")
        for assignment in assignments:
            notify_user(
                assignment.assignee, NotificationType.SYSTEM,
                _("Assigned to a project section"),
                _("You were assigned to %(discipline)s on %(sub_object)s.") % {
                    "discipline": assignment.discipline.name, "sub_object": assignment.sub_object.name,
                },
                link=f"/projects/{project.pk}/",
            )
        messages.success(request, _("Disciplines saved."))
        return redirect("projects:wizard_documents", pk=pk)

    sub_objects = list(project.sub_objects.filter(parent__isnull=True))
    selected_id = request.GET.get("sub_object") or (str(sub_objects[0].pk) if sub_objects else None)
    selected = next((s for s in sub_objects if str(s.pk) == str(selected_id)), None) if selected_id else None

    pod_objects = []
    selected_pod = None
    if selected:
        pod_objects = list(selected.pod_objects.all())
        pod_id = request.GET.get("pod_object")
        selected_pod = next((p for p in pod_objects if str(p.pk) == str(pod_id)), None) if pod_id else None

    target = selected_pod or selected
    assignments = []
    available_disciplines = []
    if target:
        assignments = list(
            SubObjectDiscipline.objects.filter(sub_object=target).select_related("discipline")
        )
        assigned_ids = {a.discipline_id for a in assignments}
        available_disciplines = list(Discipline.objects.exclude(id__in=assigned_ids))

    return render(request, "projects/project_wizard_disciplines.html", {
        "project": project, "sub_objects": sub_objects, "selected": selected,
        "pod_objects": pod_objects, "selected_pod": selected_pod, "target": target,
        "assignments": assignments, "available_disciplines": available_disciplines,
    })


@login_required
def wizard_subobject_quick_create(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    name = request.POST.get("name", "").strip()
    base_url = reverse("projects:wizard_subobjects", args=[pk])
    if not name:
        messages.error(request, _("Name is required."))
        return redirect(base_url)
    sub_object = SubObject.objects.create(project=project, name=name)
    return redirect(f"{base_url}?sub_object={sub_object.pk}")


@login_required
def wizard_pod_object_quick_create(request, pk, sub_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    parent = get_object_or_404(SubObject, pk=sub_id, project=project)
    name = request.POST.get("name", "").strip()
    base_url = reverse("projects:wizard_subobjects", args=[pk])
    if not name:
        messages.error(request, _("Name is required."))
        return redirect(_next_or(request, project, f"{base_url}?sub_object={sub_id}"))
    SubObject.objects.create(project=project, parent=parent, name=name)
    return redirect(_next_or(request, project, f"{base_url}?sub_object={sub_id}"))


@login_required
def wizard_subobjects_import_template(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project):
        raise PermissionDenied
    wb = build_subobjects_import_template()
    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="object_structure_template.xlsx"'
    wb.save(response)
    return response


@login_required
def wizard_subobjects_import(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    base_url = reverse("projects:wizard_subobjects", args=[pk])
    uploaded = request.FILES.get("file")
    if not uploaded:
        messages.error(request, _("Choose a file to upload."))
        return redirect(base_url)
    try:
        objects_created, pods_created = import_subobjects_from_excel(project, uploaded)
    except InvalidExcelStructureError as exc:
        messages.error(request, str(exc))
        return redirect(base_url)
    messages.success(
        request,
        _("Imported: %(objects)d objects, %(pods)d pod objects.")
        % {"objects": objects_created, "pods": pods_created},
    )
    return redirect(base_url)


@login_required
def wizard_discipline_assign(request, pk, sub_id, discipline_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    sub_object = get_object_or_404(SubObject, pk=sub_id, project=project)
    discipline = get_object_or_404(Discipline, pk=discipline_id)
    instance = SubObjectDiscipline.objects.filter(sub_object=sub_object, discipline=discipline).first()
    form = SubObjectDisciplineForm(request.POST, instance=instance, discipline=discipline)
    base_url = reverse("projects:wizard_disciplines", args=[pk])
    query = _wizard_discipline_query(sub_object)
    if form.is_valid():
        assignment = form.save(commit=False)
        assignment.sub_object = sub_object
        assignment.discipline = discipline
        assignment.save()
        messages.success(request, _("Section saved."))
    else:
        messages.error(request, form.errors.as_text())
    return redirect(_next_or(request, project, f"{base_url}?{query}"))


@login_required
def wizard_discipline_bulk_add(request, pk, sub_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    sub_object = get_object_or_404(SubObject, pk=sub_id, project=project)
    base_url = reverse("projects:wizard_disciplines", args=[pk])
    query = _wizard_discipline_query(sub_object)
    discipline_ids = request.POST.getlist("disciplines")
    if not discipline_ids:
        messages.error(request, _("Select at least one discipline."))
        return redirect(f"{base_url}?{query}")
    for discipline in Discipline.objects.filter(id__in=discipline_ids):
        SubObjectDiscipline.objects.get_or_create(sub_object=sub_object, discipline=discipline)
    messages.success(request, _("Disciplines added."))
    return redirect(f"{base_url}?{query}")


@login_required
def wizard_discipline_remove(request, pk, sub_id, discipline_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    sub_object = get_object_or_404(SubObject, pk=sub_id, project=project)
    base_url = reverse("projects:wizard_disciplines", args=[pk])
    query = _wizard_discipline_query(sub_object)
    SubObjectDiscipline.objects.filter(sub_object=sub_object, discipline_id=discipline_id).delete()
    messages.success(request, _("Discipline removed."))
    return redirect(_next_or(request, project, f"{base_url}?{query}"))


@login_required
def wizard_discipline_weights_save(request, pk, sub_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    sub_object = get_object_or_404(SubObject, pk=sub_id, project=project)
    base_url = reverse("projects:wizard_disciplines", args=[pk])
    query = _wizard_discipline_query(sub_object)

    error = _apply_discipline_weight_updates(sub_object, request.POST)
    if error:
        messages.error(request, error)
        return redirect(f"{base_url}?{query}")

    messages.success(request, _("Weights and progress saved."))
    return redirect(f"{base_url}?{query}")


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
    documents_by_type = {}
    for doc in Document.objects.filter(project=project, doc_type__in=doc_type_keys).order_by("-created_at"):
        documents_by_type.setdefault(doc.doc_type, []).append(doc)
    checklist = [
        {"key": key, "label": label, "documents": documents_by_type.get(key, [])}
        for key, label in WIZARD_DOC_TYPES
    ]
    return render(request, "projects/project_wizard_documents.html", {
        "project": project, "checklist": checklist,
    })


@login_required
def project_documents_download_zip(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if project not in visible_projects_for(request.user):
        raise PermissionDenied
    doc_type_keys = [key for key, _label in WIZARD_DOC_TYPES]
    documents = Document.objects.filter(project=project, doc_type__in=doc_type_keys).exclude(file="")
    if not documents.exists():
        messages.error(request, _("There are no source files to download yet."))
        return redirect("projects:detail", pk=pk)

    buffer = io.BytesIO()
    used_names = set()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for document in documents:
            arcname = document.name or f"{document.pk}"
            if arcname in used_names:
                stem, _dot, ext = arcname.rpartition(".")
                arcname = f"{stem or arcname}-{document.pk.hex[:8]}{('.' + ext) if ext else ''}"
            used_names.add(arcname)
            with document.file.open("rb") as fh:
                archive.writestr(arcname, fh.read())

    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = f'attachment; filename="{project.name}-source-files.zip"'
    return response


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

    uploaded_files = request.FILES.getlist("file")
    if not uploaded_files:
        return JsonResponse({"error": _("No file was uploaded.")}, status=400)

    created = []
    for uploaded in uploaded_files:
        form = ProjectWizardDocumentForm(request.POST, {"file": uploaded})
        if not form.is_valid():
            return JsonResponse({"error": " ".join(form.errors.get("file", []))}, status=400)

    for uploaded in uploaded_files:
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
        created.append({"id": str(document.pk), "name": document.name})

    return JsonResponse({"documents": created})


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
        messages.success(request, _("Project saved."))
        return redirect("projects:detail", pk=pk)
    return render(request, "projects/project_wizard_confirm.html", {
        "project": project, "documents": documents,
    })
