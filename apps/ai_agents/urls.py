from django.urls import path

from . import views

app_name = "ai_agents"

urlpatterns = [
    path("", views.ai_dashboard, name="dashboard"),
    path("run-deadline/", views.run_deadline_now, name="run_deadline"),
]
