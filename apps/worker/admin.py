from django.contrib import admin

from .models import WorkerJob, WorkerNode


@admin.register(WorkerJob)
class WorkerJobAdmin(admin.ModelAdmin):
    list_display = ["kind", "document", "status", "worker", "attempts", "created_at", "finished_at"]
    list_filter = ["status", "kind"]
    search_fields = ["document__name", "error"]
    readonly_fields = ["document", "version", "result_document", "requested_by", "result", "error",
                       "worker", "attempts", "created_at", "started_at", "finished_at"]


@admin.register(WorkerNode)
class WorkerNodeAdmin(admin.ModelAdmin):
    list_display = ["name", "last_seen", "version"]
