from django.contrib import admin

from .models import EmployeeContract, FinanceSettings, FinancialRecord


@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    list_display = ["project", "type", "amount", "currency", "account", "status", "date"]
    list_filter = ["type", "status", "account"]


@admin.register(EmployeeContract)
class EmployeeContractAdmin(admin.ModelAdmin):
    list_display = ["user", "project", "sub_object", "pod_object", "amount", "currency", "paid", "status"]
    list_filter = ["status"]


@admin.register(FinanceSettings)
class FinanceSettingsAdmin(admin.ModelAdmin):
    list_display = ["usd_rate", "updated_by", "updated_at"]

    def has_add_permission(self, request):
        return not FinanceSettings.objects.exists()
