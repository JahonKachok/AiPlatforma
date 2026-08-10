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
    path("<uuid:pk>/update-client/", views.project_update_client, name="update_client"),
    path("<uuid:pk>/wizard/subobjects/", views.project_wizard_subobjects, name="wizard_subobjects"),
    path(
        "<uuid:pk>/wizard/subobjects/quick-create/",
        views.wizard_subobject_quick_create, name="wizard_subobject_quick_create",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/import/",
        views.wizard_subobjects_import, name="wizard_subobjects_import",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/import-template/",
        views.wizard_subobjects_import_template, name="wizard_subobjects_import_template",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/disciplines/<uuid:discipline_id>/assign/",
        views.wizard_discipline_assign, name="wizard_discipline_assign",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/pod-objects/quick-create/",
        views.wizard_pod_object_quick_create, name="wizard_pod_object_quick_create",
    ),
    path("<uuid:pk>/wizard/disciplines/", views.project_wizard_disciplines, name="wizard_disciplines"),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/disciplines/bulk-add/",
        views.wizard_discipline_bulk_add, name="wizard_discipline_bulk_add",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/disciplines/<uuid:discipline_id>/remove/",
        views.wizard_discipline_remove, name="wizard_discipline_remove",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/disciplines/weights/",
        views.wizard_discipline_weights_save, name="wizard_discipline_weights_save",
    ),
    path("<uuid:pk>/wizard/documents/", views.project_wizard_documents, name="wizard_documents"),
    path(
        "<uuid:pk>/wizard/documents/upload/",
        views.project_wizard_document_upload, name="wizard_document_upload",
    ),
    path(
        "<uuid:pk>/wizard/documents/<uuid:doc_id>/delete/",
        views.project_wizard_document_delete, name="wizard_document_delete",
    ),
    path(
        "<uuid:pk>/documents/download-zip/",
        views.project_documents_download_zip, name="documents_download_zip",
    ),
    path("<uuid:pk>/wizard/confirm/", views.project_wizard_confirm, name="wizard_confirm"),
]
