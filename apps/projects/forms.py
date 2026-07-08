from django import forms

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin

from .models import Project, ProjectMember, Section, SubObject


class ProjectForm(StyledFormMixin, forms.ModelForm):
    gip = forms.ModelChoiceField(
        queryset=User.objects.filter(role__in=[User.Role.GIP, User.Role.MANAGER, User.Role.ADMIN]),
        required=False, label="GIP",
    )

    class Meta:
        model = Project
        fields = [
            "name", "description", "client_name", "client_contact", "address",
            "stage", "status", "start_date", "deadline", "budget", "paid_amount",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
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


class SubObjectForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = SubObject
        fields = ["name", "address", "gip", "status"]


class SectionForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Section
        fields = ["sub_object", "code", "name", "gip", "status"]

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["sub_object"].queryset = project.sub_objects.all()
