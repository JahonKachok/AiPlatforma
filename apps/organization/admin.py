from django.contrib import admin

from .models import Department, DepartmentMember, OrganizationalUnit, ReportingRelationship


class OrganizationalUnitInline(admin.TabularInline):
    model = OrganizationalUnit
    extra = 0


class DepartmentMemberInline(admin.TabularInline):
    model = DepartmentMember
    extra = 0


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "head", "status"]
    list_filter = ["status"]
    search_fields = ["name", "code"]
    inlines = [OrganizationalUnitInline]


@admin.register(OrganizationalUnit)
class OrganizationalUnitAdmin(admin.ModelAdmin):
    list_display = ["name", "department", "manager", "level", "status"]
    inlines = [DepartmentMemberInline]


@admin.register(ReportingRelationship)
class ReportingRelationshipAdmin(admin.ModelAdmin):
    list_display = ["subordinate", "manager", "department", "is_direct"]
