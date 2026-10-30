from django.contrib import admin

from .models import (
    CalendarDay, CipherRule, Contract, DisciplineConfig, OperationInfo, PersonSettings, PlanRow, ProgressReport,
    PultSettings, StageConfig, TaskTemplate, TaskWorkflow,
)


@admin.register(PlanRow)
class PlanRowAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "wbs", "code", "name", "kind", "owner", "in_plan", "calc_start", "calc_finish")
    list_filter = ("project", "kind", "in_plan")
    search_fields = ("name", "code", "doc")


@admin.register(DisciplineConfig)
class DisciplineConfigAdmin(admin.ModelAdmin):
    list_display = ("discipline", "duration", "links", "latin_code", "doc_type", "needs_estimate", "order")
    list_editable = ("duration", "links", "latin_code", "doc_type", "needs_estimate", "order")


@admin.register(CipherRule)
class CipherRuleAdmin(admin.ModelAdmin):
    list_display = ("project", "prefix", "stage", "code", "digits", "common")


@admin.register(StageConfig)
class StageConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "weight", "days", "role", "order")
    list_editable = ("weight", "days", "role", "order")


@admin.register(PersonSettings)
class PersonSettingsAdmin(admin.ModelAdmin):
    list_display = ("user", "pay_type", "norm_hours", "stage_role")
    list_editable = ("pay_type", "norm_hours", "stage_role")
    raw_id_fields = ("user",)


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("code", "project", "side", "name", "section", "currency", "amount", "status", "source")
    list_filter = ("side", "status", "currency", "project")
    search_fields = ("code", "name", "note")
    raw_id_fields = ("user", "employee_contract")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from .finance import sync_employee_contract
        sync_employee_contract(obj)


@admin.register(OperationInfo)
class OperationInfoAdmin(admin.ModelAdmin):
    list_display = ("number", "record", "counterparty", "category", "method", "contract", "offset")
    raw_id_fields = ("record", "contract")


@admin.register(TaskWorkflow)
class TaskWorkflowAdmin(admin.ModelAdmin):
    list_display = ("number", "task", "status", "days", "start_date", "done", "reworks", "flow")
    list_filter = ("status", "flow")
    search_fields = ("number", "task__title")
    raw_id_fields = ("task",)


@admin.register(ProgressReport)
class ProgressReportAdmin(admin.ModelAdmin):
    list_display = ("date", "task", "author", "done", "status", "comment")
    list_filter = ("date",)
    raw_id_fields = ("task", "author")


@admin.register(CalendarDay)
class CalendarDayAdmin(admin.ModelAdmin):
    list_display = ("date", "is_workday", "note")


@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "dept", "days", "hours")
    list_filter = ("dept",)


@admin.register(PultSettings)
class PultSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not PultSettings.objects.exists()
