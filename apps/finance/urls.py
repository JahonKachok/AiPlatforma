from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.finance_home, name="home"),
    path("projects/<uuid:project_pk>/records/add/", views.finance_record_create, name="add_record"),
    path("records/<uuid:pk>/delete/", views.finance_record_delete, name="delete_record"),
    path("transactions/add/", views.transaction_create, name="add_transaction"),
    path("rate/update/", views.update_exchange_rate, name="update_rate"),
    path("rate/update-poytaxtbank/", views.update_exchange_rate_poytaxtbank, name="update_rate_poytaxtbank"),
    path("employee-contracts/add/", views.employee_contract_create, name="add_employee_contract"),
    path("employee-contracts/<uuid:pk>/delete/", views.employee_contract_delete, name="delete_employee_contract"),
    path("employee-contracts/pay/", views.employee_contract_pay, name="pay_employee_contract"),
    path("cash-flow/export/", views.cash_flow_export, name="cash_flow_export"),
    path("administrative-expenses/add/", views.administrative_expense_create, name="add_administrative_expense"),
    path(
        "administrative-expenses/<uuid:pk>/delete/",
        views.administrative_expense_delete,
        name="delete_administrative_expense",
    ),
]
