from django.urls import path

from . import views

app_name = "organization"

urlpatterns = [
    path("", views.department_list, name="list"),
    path("new/", views.department_create, name="create"),
    path("<uuid:pk>/edit/", views.department_update, name="update"),
    path("<uuid:pk>/delete/", views.department_delete, name="delete"),
    path("<uuid:department_pk>/units/add/", views.unit_create, name="add_unit"),
    path("units/<uuid:pk>/delete/", views.unit_delete, name="delete_unit"),
    path("units/<uuid:unit_pk>/members/add/", views.member_add, name="add_member"),
    path("members/<uuid:pk>/remove/", views.member_remove, name="remove_member"),
]
