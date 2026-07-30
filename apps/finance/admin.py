from django.contrib import admin

from .models import (
    Contract,
    Contractor,
    CostCode,
    EmployeeContract,
    FinancialRecord,
    PaymentApprovalStage,
    PaymentRequest,
)


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


@admin.register(CostCode)
class CostCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "category", "project", "budget"]
    list_filter = ["project"]
    search_fields = ["code", "category"]


@admin.register(Contractor)
class ContractorAdmin(admin.ModelAdmin):
    list_display = ["name", "phone"]
    search_fields = ["name"]


class PaymentApprovalStageInline(admin.TabularInline):
    model = PaymentApprovalStage
    extra = 0


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = ["contractor", "project", "cost_code", "amount", "retainage_amount", "status", "created_at"]
    list_filter = ["status", "payment_type"]
    inlines = [PaymentApprovalStageInline]
