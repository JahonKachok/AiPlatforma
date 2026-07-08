from django.urls import path

from . import views

app_name = "finance"

urlpatterns = [
    path("", views.finance_home, name="home"),
    path("projects/<uuid:project_pk>/records/add/", views.finance_record_create, name="add_record"),
    path("records/<uuid:pk>/delete/", views.finance_record_delete, name="delete_record"),
    path("projects/<uuid:project_pk>/contracts/add/", views.contract_create, name="add_contract"),
    path("employee-contracts/add/", views.employee_contract_create, name="add_employee_contract"),
    path("employee-contracts/<uuid:pk>/delete/", views.employee_contract_delete, name="delete_employee_contract"),
]
