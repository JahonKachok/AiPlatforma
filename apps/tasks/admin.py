from django.contrib import admin

from .models import Task, TaskAttachment, TaskComment


class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0


class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "assignee", "status", "priority", "deadline"]
    list_filter = ["status", "priority"]
    search_fields = ["title"]
    inlines = [TaskCommentInline, TaskAttachmentInline]
