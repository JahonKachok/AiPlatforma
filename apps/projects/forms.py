from django import forms
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin

from .models import Project, ProjectMember, Section, SubObject


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        gip_field = self.fields.pop("gip")
        self.fields["gip"] = gip_field

    def save(self, commit=True):
        project = super().save(commit=commit)
        gip = self.cleaned_data.get("gip")
        if commit and gip:
            ProjectMember.objects.update_or_create(
                project=project, user=gip, defaults={"role_in_project": "gip"}
            )
        return project


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
        fields = ["name", "address", "gip", "status"]
        help_texts = {
            "name": _("The object's name."),
            "address": _("The object's address (optional)."),
            "gip": _("The chief architect (GIP) responsible for the object (optional)."),
            "status": _("The object's current status."),
        }


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
