from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("new/", views.project_create, name="create"),
    path("<uuid:pk>/", views.project_detail, name="detail"),
    path("<uuid:pk>/edit/", views.project_update, name="update"),
    path("<uuid:pk>/delete/", views.project_delete, name="delete"),
    path("<uuid:pk>/history/", views.project_history, name="history"),
    path("<uuid:pk>/members/add/", views.project_add_member, name="add_member"),
    path("<uuid:pk>/members/<uuid:user_id>/remove/", views.project_remove_member, name="remove_member"),
    path("<uuid:pk>/objects/add/", views.project_add_subobject, name="add_subobject"),
    path("<uuid:pk>/sections/add/", views.project_add_section, name="add_section"),
]
