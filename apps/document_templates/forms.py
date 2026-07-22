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
        help_texts = {
            "name": "Shablon nomi — hujjat yaratishda ro'yxatda shu nom bilan ko'rinadi.",
            "template_type": "Shablon qaysi hujjat turi uchun ekanligi (shartnoma, akt va h.k.).",
            "description": "Shablon haqida qisqa izoh (ixtiyoriy).",
            "content": "Hujjat matni. {{client_name}}, {{project_name}}, {{budget}}, {{deadline}} kabi "
                       "{{placeholder}} tokenlari hujjat generatsiya qilinganda haqiqiy qiymatlarga almashtiriladi.",
        }


class TemplateGenerateForm(StyledFormMixin, forms.Form):
    project = forms.ModelChoiceField(
        queryset=Project.objects.none(),
        help_text="Hujjat qaysi loyiha uchun generatsiya qilinishi — {{placeholder}} tokenlari shu loyiha ma'lumotlari bilan to'ldiriladi.",
    )
    employee = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True), required=False,
        help_text="Hujjatda xodim ma'lumoti kerak bo'lsa (masalan shartnoma), shu yerdan tanlanadi (ixtiyoriy).",
    )
    save_as_document = forms.BooleanField(
        required=False, initial=True,
        help_text="Belgilansa, generatsiya qilingan hujjat loyihaning 'Hujjatlar' bo'limiga ham saqlanadi.",
    )

    def __init__(self, *args, projects=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = projects if projects is not None else Project.objects.all()
