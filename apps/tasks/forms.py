from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import Task, TaskAttachment, TaskComment
from .permissions import allowed_status_targets, is_privileged


class TaskForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Task
        fields = ["title", "description", "project", "section", "assignee", "status", "priority", "deadline"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "deadline": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "title": _("A short, clear title for the task."),
            "description": _("Details about the task: what needs to be done, what result is expected."),
            "project": _("Which project the task belongs to."),
            "section": _("Which section within the project it belongs to (optional)."),
            "assignee": _("The employee responsible for completing the task. If set, they get a notification."),
            "status": _("The task's current status (to do, in progress, done, etc.)."),
            "priority": _("The task's priority level."),
            "deadline": _("The deadline set for completing the task."),
        }

    def __init__(self, *args, project=None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["section"].queryset = project.sections.all()
            self.fields["project"].initial = project
        if user is not None and not is_privileged(user):
            if self.instance.pk:
                allowed = {self.instance.status} | allowed_status_targets(user, self.instance)
            else:
                allowed = {Task.Status.NEW}
            self.fields["status"].choices = [
                (value, label) for value, label in Task.Status.choices if value in allowed
            ]

    def clean(self):
        cleaned = super().clean()
        project, section, assignee = cleaned.get("project"), cleaned.get("section"), cleaned.get("assignee")
        if section and project and section.project_id != project.id:
            self.add_error("section", _("This section doesn't belong to the selected project."))
        if section and assignee and not assignee.disciplines.filter(pk=section.discipline_id).exists():
            self.add_error("assignee", _("The assignee doesn't have this section's discipline."))
        return cleaned


class TaskCommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TaskComment
        fields = ["content"]
        widgets = {"content": forms.Textarea(attrs={"rows": 2, "placeholder": "Write a comment..."})}
        help_texts = {"content": _("Write your comment or question about the task here.")}


class TaskAttachmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TaskAttachment
        fields = ["file"]
        help_texts = {"file": _("Upload a file related to the task (maximum size — 50MB).")}
