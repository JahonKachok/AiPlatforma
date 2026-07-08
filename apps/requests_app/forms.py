from django import forms

from apps.core.forms import StyledFormMixin

from .models import Request, RequestComment


class RequestForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Request
        fields = ["title", "description", "type", "project", "assignee", "status", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class RequestCommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = RequestComment
        fields = ["content"]
        widgets = {"content": forms.TextInput(attrs={"placeholder": "Write a comment..."})}
