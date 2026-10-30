from django.urls import path

from . import views

app_name = "pult"

urlpatterns = [
    path("", views.pult_page, name="page"),
    path("app/", views.pult_app, name="app"),
    path("api/data/", views.api_data, name="api_data"),
    path("api/tasks/", views.api_create, name="api_create"),
    path("api/tasks/<int:number>/edit/", views.api_edit, name="api_edit"),
    path("api/tasks/<int:number>/action/", views.api_action, name="api_action"),
    path("api/report/", views.api_report, name="api_report"),
    path("api/plan/", views.api_plan, name="api_plan"),
    path("api/plan/import/", views.api_plan_import, name="api_plan_import"),
    path("api/sync/", views.api_sync, name="api_sync"),
    path("api/disciplines/", views.api_discipline, name="api_discipline"),
    path("api/ciphers/", views.api_cipher, name="api_cipher"),
    path("api/ops/", views.api_operations, name="api_ops"),
]
