from django.urls import path

from . import views

app_name = "ai_agents"

urlpatterns = [
    path("", views.ai_dashboard, name="dashboard"),
    path("office/", views.office, name="office"),
    path("office/data/", views.office_data, name="office_data"),
    path("office/actions/<slug:action>/", views.office_action, name="office_action"),
    path("office/status/", views.office_status, name="office_status"),
    path("run-deadline/", views.run_deadline_now, name="run_deadline"),
]
