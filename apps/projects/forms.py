from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin

from .models import Project, ProjectMember, Section, SubObject, SubObjectWorker

WIZARD_DOCUMENT_EXTENSIONS = ["pdf", "doc", "docx", "xls", "xlsx", "zip", "rar"]


class ProjectForm(StyledFormMixin, forms.ModelForm):
    gip = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=[User.Role.GIP, User.Role.MANAGER, User.Role.ADMIN]),
        required=False, label="GIP",
        help_text=_("The project's chief architect (GIP) — the employee responsible for the project (optional)."),
    )

    class Meta:
        model = Project
        fields = [
            "name", "description", "client_name", "client_contact",
            "construction_type", "sector", "object_type", "funding_source",
            "construction_area", "land_area", "construction_volume",
            "region", "district", "address", "latitude", "longitude",
            "stage", "status", "start_date", "deadline", "budget", "paid_amount",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }
        help_texts = {
            "name": _("The project's name — shown under this name in lists and reports."),
            "description": _("A short description of the project (optional)."),
            "client_name": _("The name of the client organization or person."),
            "client_contact": _("The client's contact info — phone or email."),
            "construction_type": _("The type of construction work."),
            "sector": _("The sector the project belongs to (e.g. trade, housing, education)."),
            "object_type": _("The object's category (e.g. Category II)."),
            "funding_source": _("Where the construction funding comes from."),
            "construction_area": _("The construction area, m² (optional)."),
            "land_area": _("The land plot area, m² (optional)."),
            "construction_volume": _("The construction volume (optional)."),
            "region": _("The region (viloyat) the project is located in."),
            "district": _("The district (tuman) the project is located in."),
            "address": _("The mahalla, street, and house/building number."),
            "stage": _("The project's current stage (e.g. design, construction)."),
            "status": _("The project's status (active, on hold, completed, etc.)."),
            "start_date": _("The date the project started."),
            "deadline": _("The deadline set for completing the project."),
            "budget": _("The project's total budget (amount)."),
            "paid_amount": _("The amount paid so far — shows what share of the budget has been paid."),
        }

    REQUIRED_FIELDS = [
        "name", "construction_type", "sector", "object_type", "funding_source",
        "region", "district", "address",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        gip_field = self.fields.pop("gip")
        self.fields["gip"] = gip_field
        for field_name in self.REQUIRED_FIELDS:
            self.fields[field_name].required = True

    def save(self, commit=True):
        project = super().save(commit=commit)
        gip = self.cleaned_data.get("gip")
        if commit and gip:
            ProjectMember.objects.update_or_create(
                project=project, user=gip, defaults={"role_in_project": "gip"}
            )
        return project


class ProjectClientForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "client_type", "client_name", "client_stir", "client_contact",
            "client_email", "client_contact_person", "client_position", "client_notes",
        ]
        widgets = {"client_notes": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "client_type": _("Whether the client is a legal entity or an individual."),
            "client_name": _("The name of the client organization or person."),
            "client_stir": _("The client's tax ID (STIR) — digits only (optional)."),
            "client_contact": _("The client's phone number."),
            "client_email": _("The client's email address (optional)."),
            "client_contact_person": _("The person responsible on the client's side (optional)."),
            "client_position": _("That person's position (optional)."),
            "client_notes": _("Any additional information about the client (optional)."),
        }


class ProjectWizardDocumentForm(StyledFormMixin, forms.Form):
    file = forms.FileField(
        validators=[FileExtensionValidator(WIZARD_DOCUMENT_EXTENSIONS)],
        help_text=_("Allowed formats: pdf, doc, docx, xls, xlsx, zip, rar. Maximum size — 50MB."),
    )


class ProjectMemberForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectMember
        fields = ["user", "role_in_project", "can_edit", "expires_at"]
        widgets = {"expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}
        help_texts = {
            "user": _("The employee being added to the project."),
            "role_in_project": _("The employee's role in the project (e.g. GIP, engineer)."),
            "can_edit": _("If checked, the employee can edit the project's data."),
            "expires_at": _("The date the employee's access to the project expires (optional)."),
        }


class SubObjectForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SubObject
        fields = ["name", "description", "priority", "start_date", "deadline", "gip", "status"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "name": _("The sub-object's name."),
            "description": _("A short description (optional)."),
            "priority": _("The sub-object's priority."),
            "start_date": _("When work on this sub-object starts (optional)."),
            "deadline": _("The deadline for this sub-object."),
            "gip": _("The chief architect (GIP) responsible for the object (optional)."),
            "status": _("The object's current status."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["deadline"].required = True


class SubObjectWorkerForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SubObjectWorker
        fields = ["user", "role", "deadline", "status"]
        widgets = {"deadline": forms.DateInput(attrs={"type": "date"})}
        help_texts = {
            "user": _("The employee assigned to this sub-object."),
            "role": _("Their role on this sub-object."),
            "deadline": _("Their personal deadline (optional)."),
            "status": _("Their progress status."),
        }

    def __init__(self, *args, sub_object=None, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = User.objects.filter(is_active=True)
        if sub_object is not None:
            queryset = queryset.exclude(sub_object_assignments__sub_object=sub_object)
        self.fields["user"].queryset = queryset


class SectionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Section
        fields = ["sub_object", "discipline", "name", "gip", "status"]
        help_texts = {
            "sub_object": _("Which object this sub-object belongs to."),
            "discipline": _("The work discipline (specialization) this sub-object covers."),
            "name": _("The sub-object's name."),
            "gip": _("The chief architect (GIP) responsible for the sub-object (optional)."),
            "status": _("The sub-object's current status."),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["sub_object"].queryset = project.sub_objects.all()
        self.fields["sub_object"].required = True
