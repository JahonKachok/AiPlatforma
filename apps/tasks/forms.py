from django import forms

from apps.core.forms import StyledFormMixin

from .models import Task, TaskAttachment, TaskComment


class TaskForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "project", "section", "assignee", "status", "priority", "deadline"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["section"].queryset = project.sections.all()
            self.fields["project"].initial = project


class TaskCommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ["content"]
        widgets = {"content": forms.Textarea(attrs={"rows": 2, "placeholder": "Write a comment..."})}


class TaskAttachmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TaskAttachment
        fields = ["file"]
