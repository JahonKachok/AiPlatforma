from django.urls import path

from . import views

app_name = "requests_app"

urlpatterns = [
    path("", views.request_list, name="list"),
    path("new/", views.request_create, name="create"),
    path("<uuid:pk>/", views.request_detail, name="detail"),
    path("<uuid:pk>/edit/", views.request_update, name="update"),
    path("<uuid:pk>/delete/", views.request_delete, name="delete"),
]
