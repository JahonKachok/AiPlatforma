from django import forms
from django.utils.translation import gettext_lazy as _

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
        help_texts = {
            "name": _("The template's name — shown under this name in the list when creating a document."),
            "template_type": _("Which document type the template is for (contract, act, etc.)."),
            "description": _("A short description of the template (optional)."),
            "content": _("The document text. {{placeholder}} tokens such as {{client_name}}, {{project_name}}, "
                        "{{budget}}, {{deadline}} are replaced with real values when the document is generated."),
        }


class TemplateGenerateForm(StyledFormMixin, forms.Form):
    project = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        help_text=_("Which project the document is generated for — {{placeholder}} tokens are filled with this project's data."),
    )
    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True), required=False,
        help_text=_("If the document needs employee info (e.g. a contract), select it here (optional)."),
    )
    save_as_document = forms.BooleanField(
        required=False, initial=True,
        help_text=_("If checked, the generated document is also saved to the project's 'Documents' section."),
    )

    def __init__(self, *args, projects=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = projects if projects is not None else Project.objects.all()
