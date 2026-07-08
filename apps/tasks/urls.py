from django.urls import path

from . import views

app_name = "tasks"

urlpatterns = [
    path("", views.task_board, name="board"),
    path("new/", views.task_create, name="create"),
    path("<uuid:pk>/", views.task_detail, name="detail"),
    path("<uuid:pk>/edit/", views.task_update, name="update"),
    path("<uuid:pk>/delete/", views.task_delete, name="delete"),
    path("<uuid:pk>/status/", views.task_update_status, name="update_status"),
    path("<uuid:pk>/comments/<uuid:comment_id>/delete/", views.task_comment_delete, name="delete_comment"),
    path("<uuid:pk>/attachments/", views.task_attachment_upload, name="upload_attachment"),
    path("<uuid:pk>/attachments/<uuid:attachment_id>/delete/", views.task_attachment_delete, name="delete_attachment"),
]
