from django import forms

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin
from apps.projects.models import Project

from .models import DocumentTemplate


class DocumentTemplateForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = DocumentTemplate
        fields = ["name", "template_type", "description", "content"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "content": forms.Textarea(attrs={"rows": 12, "class": "font-mono"}),
        }


class TemplateGenerateForm(StyledFormMixin, forms.Form):
    project = forms.ModelChoiceField(queryset=Project.objects.none())
    employee = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True), required=False)
    save_as_document = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, projects=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = projects if projects is not None else Project.objects.all()
