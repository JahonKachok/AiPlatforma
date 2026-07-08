from django import forms
from django.forms import formset_factory

from apps.accounts.models import User
from apps.core.forms import StyledFormMixin

from .models import Document


class DocumentUploadForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Document
        fields = ["name", "doc_type", "project", "section", "version", "deadline", "file"]
        widgets = {"deadline": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["section"].queryset = project.sections.all()
            self.fields["project"].initial = project


class DocumentVersionForm(StyledFormMixin, forms.Form):
    file = forms.FileField(label="File")
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))


class ApprovalStageAssignForm(StyledFormMixin, forms.Form):
    stage_name = forms.CharField(max_length=100)
    reviewer = forms.ModelChoiceField(queryset=User.objects.filter(is_active=True))


ApprovalStageFormSet = formset_factory(ApprovalStageAssignForm, extra=1, can_delete=True)


class ApprovalReviewForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(choices=[
        ("approved", "Approve"), ("rejected", "Reject"), ("revision", "Needs revision"),
    ], widget=forms.RadioSelect)
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
