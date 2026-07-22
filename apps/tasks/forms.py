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
        help_texts = {
            "title": "Vazifaning qisqa va aniq nomi.",
            "description": "Vazifa haqida batafsil ma'lumot: nima qilish kerak, qanday natija kutilyapti.",
            "project": "Vazifa qaysi loyihaga tegishli ekanligi.",
            "section": "Loyiha ichidagi qaysi bo'limga (section) tegishli ekanligi (ixtiyoriy).",
            "assignee": "Vazifani bajarishga mas'ul xodim. Tanlansa, unga bildirishnoma yuboriladi.",
            "status": "Vazifaning joriy holati (bajarilishi kerak, jarayonda, bajarildi va h.k.).",
            "priority": "Vazifaning muhimlik darajasi.",
            "deadline": "Vazifani bajarish uchun belgilangan muddat.",
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
        help_texts = {"content": "Vazifa bo'yicha izoh yoki savolingizni shu yerga yozing."}


class TaskAttachmentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = TaskAttachment
        fields = ["file"]
        help_texts = {"file": "Vazifaga tegishli faylni yuklash (maksimal hajm — 50MB)."}
