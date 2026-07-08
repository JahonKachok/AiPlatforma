from django.contrib import admin

from .models import Project, ProjectMember, Section, SubObject


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 0


class SubObjectInline(admin.TabularInline):
    model = SubObject
    extra = 0


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "client_name", "stage", "status", "budget", "paid_amount", "created_by"]
    list_filter = ["stage", "status"]
    search_fields = ["name", "client_name"]
    inlines = [ProjectMemberInline, SubObjectInline, SectionInline]


@admin.register(SubObject)
class SubObjectAdmin(admin.ModelAdmin):
    list_display = ["name", "project", "gip", "status"]
    list_filter = ["status"]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "project", "gip", "status"]
    list_filter = ["status"]


@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ["project", "user", "role_in_project", "can_edit", "expires_at"]
