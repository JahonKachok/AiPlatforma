from django import forms

from apps.core.forms import StyledFormMixin

from .models import Request, RequestComment


class RequestForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Request
        fields = ["title", "description", "type", "project", "assignee", "status", "priority"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}
        help_texts = {
            "title": "So'rovning qisqa va aniq nomi. Masalan: \"Fasad rangini o'zgartirish\".",
            "description": "So'rov haqida batafsil ma'lumot: nima kerak, nima uchun kerak, qanday natija kutilyapti.",
            "type": "So'rov turi — Change: mavjud narsani o'zgartirish; Clarification: savol/aniqlik so'rash; "
                    "Improvement: yaxshilash taklifi; Issue: xato yoki nosozlik haqida xabar.",
            "project": "So'rov qaysi loyihaga tegishli. Tanlangan loyiha a'zolari bu so'rovni ko'ra oladi.",
            "assignee": "So'rovni bajarishga mas'ul xodim. Tanlansa, unga avtomatik bildirishnoma yuboriladi.",
            "status": "So'rovning joriy holati: Open (ochiq) → In progress (jarayonda) → Resolved (hal qilindi) → Closed (yopilgan).",
            "priority": "So'rovning muhimlik darajasi: Low, Medium yoki High.",
        }


class RequestCommentForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = RequestComment
        fields = ["content"]
        widgets = {"content": forms.TextInput(attrs={"placeholder": "Write a comment..."})}
        help_texts = {"content": "So'rov bo'yicha izoh yoki javobingizni shu yerga yozing."}
