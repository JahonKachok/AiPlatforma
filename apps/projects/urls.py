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
        "<uuid:pk>/wizard/subobjects/create/",
        views.wizard_subobject_create, name="wizard_subobject_create",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/update/",
        views.wizard_subobject_update, name="wizard_subobject_update",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/delete/",
        views.wizard_subobject_delete, name="wizard_subobject_delete",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/duplicate/",
        views.wizard_subobject_duplicate, name="wizard_subobject_duplicate",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/reorder/",
        views.wizard_subobject_reorder, name="wizard_subobject_reorder",
    ),
    path(
        "<uuid:pk>/wizard/workers/search/",
        views.wizard_worker_search, name="wizard_worker_search",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/workers/add/",
        views.wizard_worker_add, name="wizard_worker_add",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/workers/<uuid:worker_id>/remove/",
        views.wizard_worker_remove, name="wizard_worker_remove",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/tasks/create/",
        views.wizard_task_create, name="wizard_task_create",
    ),
    path(
        "<uuid:pk>/wizard/tasks/<uuid:task_id>/update/",
        views.wizard_task_update, name="wizard_task_update",
    ),
    path(
        "<uuid:pk>/wizard/tasks/<uuid:task_id>/delete/",
        views.wizard_task_delete, name="wizard_task_delete",
    ),
    path(
        "<uuid:pk>/wizard/subobjects/<uuid:sub_id>/tasks/reorder/",
        views.wizard_task_reorder, name="wizard_task_reorder",
    ),
    path(
        "<uuid:pk>/wizard/tasks/<uuid:task_id>/checklist/add/",
        views.wizard_checklist_add, name="wizard_checklist_add",
    ),
    path(
        "<uuid:pk>/wizard/checklist/<uuid:item_id>/toggle/",
        views.wizard_checklist_toggle, name="wizard_checklist_toggle",
    ),
    path(
        "<uuid:pk>/wizard/checklist/<uuid:item_id>/delete/",
        views.wizard_checklist_delete, name="wizard_checklist_delete",
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
    path("<uuid:pk>/wizard/confirm/", views.project_wizard_confirm, name="wizard_confirm"),
]
