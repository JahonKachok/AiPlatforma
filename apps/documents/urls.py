from django.urls import path

from . import views

app_name = "documents"

urlpatterns = [
    path("", views.document_list, name="list"),
    path("upload/", views.document_upload, name="upload"),
    path("bulk-download/", views.document_bulk_download, name="bulk_download"),
    path("<uuid:pk>/", views.document_detail, name="detail"),
    path("<uuid:pk>/download/", views.document_download, name="download"),
    path("<uuid:pk>/delete/", views.document_delete, name="delete"),
    path("<uuid:pk>/versions/add/", views.document_add_version, name="add_version"),
    path("<uuid:pk>/quick-approve/", views.document_quick_approve, name="quick_approve"),
    path("<uuid:pk>/stages/", views.approval_stage_assign, name="assign_stages"),
    path("approvals/", views.approvals_list, name="approvals"),
    path("stages/<uuid:stage_id>/review/", views.approval_stage_review, name="review_stage"),
]
