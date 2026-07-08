from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path("unread-count/", views.unread_count, name="unread_count"),
    path("recent/", views.recent_partial, name="recent"),
    path("<uuid:pk>/read/", views.mark_read, name="mark_read"),
    path("read-all/", views.mark_all_read, name="mark_all_read"),
    path("<uuid:pk>/delete/", views.delete_notification, name="delete"),
]
