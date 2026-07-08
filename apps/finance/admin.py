from django.contrib import admin

from .models import Contract, EmployeeContract, FinancialRecord


@admin.register(FinancialRecord)
class FinancialRecordAdmin(admin.ModelAdmin):
    list_display = ["project", "type", "amount", "currency", "status", "date"]
    list_filter = ["type", "status"]


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ["client_name", "project", "contract_number", "amount", "status"]
    list_filter = ["status"]


@admin.register(EmployeeContract)
class EmployeeContractAdmin(admin.ModelAdmin):
    list_display = ["user", "project", "amount", "advance", "paid", "status"]
    list_filter = ["status"]
