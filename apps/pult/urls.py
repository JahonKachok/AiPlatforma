from django.urls import path
from django.views.generic import RedirectView

from . import views
from .nav import SECTIONS, section_url_name

app_name = "pult"

# Ildiz URL'ga ulanadi (aiplatforma/urls.py): bo'lim sahifalari o'z
# menyusining yo'lida turadi, masalan /tasks/gantt/, shunda yon menyuda
# tegishli band yonadi.
urlpatterns = [
    # Eski /pult/ xatcho'plari uchun.
    path("pult/", RedirectView.as_view(pattern_name="pult:section_work"), name="page"),
    path("pult/app/", views.pult_app, name="app"),
    path("pult/api/data/", views.api_data, name="api_data"),
    path("pult/api/tasks/", views.api_create, name="api_create"),
    path("pult/api/tasks/<int:number>/edit/", views.api_edit, name="api_edit"),
    path("pult/api/tasks/<int:number>/action/", views.api_action, name="api_action"),
    path("pult/api/report/", views.api_report, name="api_report"),
    path("pult/api/plan/", views.api_plan, name="api_plan"),
    path("pult/api/plan/import/", views.api_plan_import, name="api_plan_import"),
    path("pult/api/sync/", views.api_sync, name="api_sync"),
    path("pult/api/disciplines/", views.api_discipline, name="api_discipline"),
    path("pult/api/ciphers/", views.api_cipher, name="api_cipher"),
    path("pult/api/ops/", views.api_operations, name="api_ops"),
    *(
        path(route, views.pult_section, {"section": section}, name=section_url_name(section))
        for section, (_group, route, _label) in SECTIONS.items()
    ),
]
