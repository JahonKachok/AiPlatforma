from django.urls import path

from . import api

app_name = "worker"

urlpatterns = [
    path("heartbeat/", api.heartbeat, name="heartbeat"),
    path("claim/", api.claim, name="claim"),
    path("jobs/<uuid:pk>/input/", api.job_input, name="input"),
    path("jobs/<uuid:pk>/result/", api.job_result, name="result"),
    path("ai/", api.ai, name="ai"),
]
