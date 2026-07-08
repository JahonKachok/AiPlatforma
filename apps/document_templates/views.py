from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.core.permissions import role_required
from apps.documents.models import AuditLog, Document
from apps.finance.models import EmployeeContract
from apps.projects.permissions import visible_projects_for

from .forms import DocumentTemplateForm, TemplateGenerateForm
from .generate import build_context, render_content, render_docx
from .models import DocumentTemplate

MANAGE_ROLES = (User.Role.ADMIN, User.Role.MANAGER, User.Role.GIP)
DELETE_ROLES = (User.Role.ADMIN, User.Role.MANAGER)


@login_required
def template_list(request):
    templates = DocumentTemplate.objects.all()
    return render(request, "document_templates/template_list.html", {
        "templates": templates,
        "can_manage": request.user.is_superuser or request.user.role in MANAGE_ROLES,
        "can_delete": request.user.is_superuser or request.user.role in DELETE_ROLES,
    })


@role_required(*MANAGE_ROLES)
def template_create(request):
    if request.method == "POST":
        form = DocumentTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            messages.success(request, _("Template created."))
            return redirect("document_templates:list")
    else:
        form = DocumentTemplateForm()
    return render(request, "document_templates/template_form.html", {"form": form, "is_create": True})


@role_required(*MANAGE_ROLES)
def template_update(request, pk):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    if request.method == "POST":
        form = DocumentTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, _("Template updated."))
            return redirect("document_templates:list")
    else:
        form = DocumentTemplateForm(instance=template)
    return render(request, "document_templates/template_form.html", {"form": form, "template": template, "is_create": False})


@role_required(*DELETE_ROLES)
def template_delete(request, pk):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    if request.method == "POST":
        template.delete()
        messages.success(request, _("Template deleted."))
        return redirect("document_templates:list")
    return render(request, "document_templates/template_confirm_delete.html", {"template": template})


@login_required
def template_generate(request, pk):
    template = get_object_or_404(DocumentTemplate, pk=pk)
    projects = visible_projects_for(request.user)
    rendered_text = None
    download_url = None

    if request.method == "POST":
        form = TemplateGenerateForm(request.POST, projects=projects)
        if form.is_valid():
            project = form.cleaned_data["project"]
            employee = form.cleaned_data.get("employee")
            employee_contract = None
            if employee:
                employee_contract = EmployeeContract.objects.filter(project=project, user=employee).first()

            context = build_context(project, employee_contract)
            rendered_text = render_content(template.content, context)
            filename, docx_file = render_docx(template.name, rendered_text)

            if form.cleaned_data.get("save_as_document"):
                document = Document.objects.create(
                    name=f"{template.name} — {project.name}",
                    doc_type=template.template_type,
                    project=project,
                    uploaded_by=request.user,
                    file=docx_file,
                    file_size=docx_file.size,
                    version="1.0",
                )
                AuditLog.log(obj=document, action="generate_from_template", user=request.user)
                download_url = document.file.url
            messages.success(request, _("Document generated."))
    else:
        form = TemplateGenerateForm(projects=projects)

    return render(request, "document_templates/template_generate.html", {
        "template": template, "form": form, "rendered_text": rendered_text, "download_url": download_url,
    })
