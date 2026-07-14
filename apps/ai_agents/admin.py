from django.contrib import admin

from .models import AILog


@admin.register(AILog)
class AILogAdmin(admin.ModelAdmin):
    list_display = ["agent", "provider", "model", "status", "duration_ms", "created_at"]
    list_filter = ["status", "provider", "agent"]
    search_fields = ["prompt", "response", "error"]
    readonly_fields = [f.name for f in AILog._meta.fields]

    def has_add_permission(self, request):
        return False
