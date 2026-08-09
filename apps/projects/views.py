import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Discipline, User
from apps.documents.models import AuditLog, Document, DocumentVersion
from apps.finance.forms import FinancialRecordForm
from apps.notifications.models import NotificationType
from apps.notifications.services import notify_user
from apps.tasks.models import Task

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
            "sub_objects__disciplines__discipline",
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

    doc_type_keys = [key for key, _label in WIZARD_DOC_TYPES]
    documents_by_type = {
        doc.doc_type: doc
        for doc in Document.objects.filter(project=project, doc_type__in=doc_type_keys)
    }
    source_files_checklist = [
        {"key": key, "label": label, "document": documents_by_type.get(key)}
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
        # PaymentRequest.cost_code is PROTECT, and CostCode cascades from Project —
        # deleting payment requests first clears that protection before the project
        # (and its cost codes) cascade-delete.
        project.payment_requests.all().delete()
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
        return redirect(f"{base_url}?sub_object={sub_id}")
    SubObject.objects.create(project=project, parent=parent, name=name)
    return redirect(f"{base_url}?sub_object={sub_id}")


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
    return redirect(f"{base_url}?{query}")


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
    return redirect(f"{base_url}?{query}")


@login_required
def wizard_discipline_weights_save(request, pk, sub_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_edit_project(request.user, project) or request.method != "POST":
        raise PermissionDenied
    sub_object = get_object_or_404(SubObject, pk=sub_id, project=project)
    base_url = reverse("projects:wizard_disciplines", args=[pk])
    query = _wizard_discipline_query(sub_object)
    assignments = list(SubObjectDiscipline.objects.filter(sub_object=sub_object))

    updates = []
    for assignment in assignments:
        try:
            weight = int(request.POST.get(f"weight_{assignment.pk}"))
            progress = int(request.POST.get(f"progress_{assignment.pk}"))
        except (TypeError, ValueError):
            messages.error(request, _("Weight and progress must be whole numbers."))
            return redirect(f"{base_url}?{query}")
        if not (0 <= weight <= 100) or not (0 <= progress <= 100):
            messages.error(request, _("Weight and progress must be between 0 and 100."))
            return redirect(f"{base_url}?{query}")
        assignment.weight = weight
        assignment.progress = progress
        updates.append(assignment)

    if updates:
        SubObjectDiscipline.objects.bulk_update(updates, ["weight", "progress"])
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
        messages.success(request, _("Project saved."))
        return redirect("projects:detail", pk=pk)
    return render(request, "projects/project_wizard_confirm.html", {
        "project": project, "documents": documents,
    })
