from django import forms
from django.forms import formset_factory
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin
from apps.projects.models import Project, SubObject

from .models import Document


class DocumentUploadForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Document
        fields = ["name", "doc_type", "project", "section", "version", "deadline", "file"]
        widgets = {"deadline": forms.DateInput(attrs={"type": "date"})}
        help_texts = {
            "name": _("The document's name — shown under this name in lists."),
            "doc_type": _("The document type (drawing, estimate, contract, etc.)."),
            "project": _("Which project the document belongs to."),
            "section": _("Which section within the project it belongs to (optional)."),
            "version": _("The document version, e.g. v1, v2.1 (optional)."),
            "deadline": _("The deadline for the document, if any (optional)."),
            "file": _("The file to upload (maximum size — 50MB)."),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["section"].queryset = project.sections.all()
            self.fields["project"].initial = project


class DocumentVersionForm(StyledFormMixin, forms.Form):
    file = forms.FileField(
        label="File", help_text=_("Upload the file for the document's new version."),
    )
    notes = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}),
        help_text=_("Briefly note what changed in this version (optional)."),
    )


class ApprovalStageAssignForm(StyledFormMixin, forms.Form):
    stage_name = forms.CharField(
        max_length=100, help_text=_("The approval stage's name (e.g. 'Chief engineer review')."),
    )
    reviewer = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        help_text=_("The employee who reviews the document at this stage."),
    )


ApprovalStageFormSet = formset_factory(ApprovalStageAssignForm, extra=1, can_delete=True)


class ApprovalReviewForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(choices=[
        ("approved", _("Approve")), ("revision", _("Send for revision")), ("rejected", _("Reject")),
    ], widget=forms.RadioSelect, help_text=_("Your decision on the document: approve, send back for revision, or reject."))
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text=_("Explain your decision — required so the author knows what to do next."),
    )
    file = forms.FileField(
        required=False,
        help_text=_("Optionally attach a file with your response (e.g. markup, corrections)."),
    )


class ApprovalSubmissionForm(StyledFormMixin, forms.Form):
    title = forms.CharField(
        max_length=255, label=_("Approval title"),
        help_text=_("A short title describing what you're submitting for approval."),
    )
    project = forms.ModelChoiceField(
        queryset=Project.objects.none(), help_text=_("Which project this belongs to."),
    )
    sub_object = forms.ModelChoiceField(
        queryset=SubObject.objects.none(), widget=forms.HiddenInput(),
        error_messages={"required": _("Select an object (and pod object, if applicable).")},
    )
    comment = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3}), label=_("Comments"),
        help_text=_("Describe what you're submitting."),
    )
    file = forms.FileField(help_text=_("The file to submit for approval."))

    def __init__(self, *args, projects=None, **kwargs):
        super().__init__(*args, **kwargs)
        if projects is not None:
            self.fields["project"].queryset = projects
            self.fields["sub_object"].queryset = SubObject.objects.filter(project__in=projects)
