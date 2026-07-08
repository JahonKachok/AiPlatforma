from django.contrib import admin

from .models import ApprovalStage, AuditLog, Document, DocumentVersion


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0


class ApprovalStageInline(admin.TabularInline):
    model = ApprovalStage
    extra = 0


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "doc_type", "version", "status", "uploaded_by"]
    list_filter = ["status", "doc_type"]
    search_fields = ["name"]
    inlines = [DocumentVersionInline, ApprovalStageInline]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "content_type", "object_id", "user", "created_at"]
    list_filter = ["action", "content_type"]
    readonly_fields = [f.name for f in AuditLog._meta.fields]
