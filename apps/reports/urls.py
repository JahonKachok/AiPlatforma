from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.reports_dashboard, name="dashboard"),
    path("export/<str:kind>/", views.report_export, name="export"),
]
