from django.contrib import admin

from .models import Request, RequestComment


class RequestCommentInline(admin.TabularInline):
    model = RequestComment
    extra = 0


@admin.register(Request)
class RequestAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "type", "status", "priority", "created_by", "assignee"]
    list_filter = ["type", "status", "priority"]
    search_fields = ["title"]
    inlines = [RequestCommentInline]
