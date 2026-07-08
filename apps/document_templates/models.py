import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class TemplateType(models.TextChoices):
    CONTRACT = "contract", _("Contract")
    ACT = "act", _("Act")
    APPENDIX = "appendix", _("Appendix")
    INVOICE = "invoice", _("Invoice")
    OTHER = "other", _("Other")


class DocumentTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    template_type = models.CharField(max_length=20, choices=TemplateType.choices, default=TemplateType.CONTRACT)
    description = models.CharField(max_length=1000, blank=True, null=True)
    content = models.TextField(help_text="Mail-merge style content using {{placeholder}} tokens.")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
