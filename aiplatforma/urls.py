from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("accounts/", include("apps.accounts.urls")),
    path("projects/", include("apps.projects.urls")),
    path("tasks/", include("apps.tasks.urls")),
    path("documents/", include("apps.documents.urls")),
    path("finance/", include("apps.finance.urls")),
    path("requests/", include("apps.requests_app.urls")),
    path("templates/", include("apps.document_templates.urls")),
    path("organization/", include("apps.organization.urls")),
    path("reports/", include("apps.reports.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("telegram/", include("apps.telegram_bot.urls")),
    path("", include("apps.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
