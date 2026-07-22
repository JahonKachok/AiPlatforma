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
        help_texts = {
            "name": "Hujjatning nomi — ro'yxatda shu nom bilan ko'rinadi.",
            "doc_type": "Hujjat turi (chizma, smeta, shartnoma va h.k.).",
            "project": "Hujjat qaysi loyihaga tegishli ekanligi.",
            "section": "Loyiha ichidagi qaysi bo'limga (section) tegishli ekanligi (ixtiyoriy).",
            "version": "Hujjat versiyasi, masalan: v1, v2.1 (ixtiyoriy).",
            "deadline": "Hujjat bo'yicha muddat bo'lsa, shu yerda ko'rsatiladi (ixtiyoriy).",
            "file": "Yuklanadigan fayl (maksimal hajm — 50MB).",
        }

    def __init__(self, *args, project=None, **kwargs):
        super().__init__(*args, **kwargs)
        if project is not None:
            self.fields["section"].queryset = project.sections.all()
            self.fields["project"].initial = project


class DocumentVersionForm(StyledFormMixin, forms.Form):
    file = forms.FileField(
        label="File", help_text="Hujjatning yangi versiyasi uchun faylni yuklang.",
    )
    notes = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Bu versiyada nima o'zgarganini qisqa yozib qo'ying (ixtiyoriy).",
    )


class ApprovalStageAssignForm(StyledFormMixin, forms.Form):
    stage_name = forms.CharField(
        max_length=100, help_text="Tasdiqlash bosqichining nomi (masalan: 'Bosh muhandis tekshiruvi').",
    )
    reviewer = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        help_text="Shu bosqichda hujjatni ko'rib chiqadigan xodim.",
    )


ApprovalStageFormSet = formset_factory(ApprovalStageAssignForm, extra=1, can_delete=True)


class ApprovalReviewForm(StyledFormMixin, forms.Form):
    status = forms.ChoiceField(choices=[
        ("approved", "Approve"), ("rejected", "Reject"), ("revision", "Needs revision"),
    ], widget=forms.RadioSelect, help_text="Hujjat bo'yicha qaroringiz: tasdiqlash, rad etish yoki qayta ko'rib chiqishga yuborish.")
    comment = forms.CharField(
        required=False, widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Qaroringiz sababini yoki izohingizni yozing (ixtiyoriy).",
    )
