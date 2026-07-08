from django.contrib import admin

from .models import DocumentTemplate


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "template_type", "created_by", "updated_at"]
    list_filter = ["template_type"]
    search_fields = ["name"]
