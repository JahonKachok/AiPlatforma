from django import forms
from django.utils.translation import gettext_lazy as _

from apps.core.forms import StyledFormMixin

from .models import Request, RequestComment


class RequestForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Request
        fields = ["title", "description", "type", "project", "assignee", "status", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "title": _("A short, clear title for the request. E.g. \"Change facade color\"."),
            "description": _("Details about the request: what is needed, why, and what result is expected."),
            "type": _("The request type — Change: modify something existing; Clarification: ask a question; "
                      "Improvement: suggest an enhancement; Issue: report a bug or defect."),
            "project": _("Which project the request belongs to. Members of the selected project can see this request."),
            "assignee": _("The employee responsible for handling the request. If set, they get an automatic notification."),
            "status": _("The request's current status: Open → In progress → Resolved → Closed."),
            "priority": _("The request's priority level: Low, Medium, or High."),
        }


class RequestCommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = RequestComment
        fields = ["content"]
        widgets = {"content": forms.TextInput(attrs={"placeholder": "Write a comment..."})}
        help_texts = {"content": _("Write your comment or reply about the request here.")}
