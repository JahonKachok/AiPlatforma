from django.urls import path

from . import views

app_name = "document_templates"

urlpatterns = [
    path("", views.template_list, name="list"),
    path("new/", views.template_create, name="create"),
    path("<uuid:pk>/edit/", views.template_update, name="update"),
    path("<uuid:pk>/delete/", views.template_delete, name="delete"),
    path("<uuid:pk>/generate/", views.template_generate, name="generate"),
]
