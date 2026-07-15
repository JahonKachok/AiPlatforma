from django.urls import path

from . import admin_ops, views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("search/", views.global_search, name="search"),
    path("dark-mode/", views.set_dark_mode, name="set_dark_mode"),
    path("admin/backups/", admin_ops.backup_list, name="backup_list"),
    path("admin/backups/<str:filename>/download/", admin_ops.backup_download, name="backup_download"),
    path("admin/backups/<str:filename>/delete/", admin_ops.backup_delete, name="backup_delete"),
]
