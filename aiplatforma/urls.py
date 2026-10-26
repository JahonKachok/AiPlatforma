from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path, re_path

from apps.core.views import protected_media

# /django-admin/ ning o'z login sahifasi 2FA'ni ham, urinishlar cheklovini ham
# chetlab o'tardi: superuser parolini shu yerda cheksiz tanlab ko'rish mumkin
# edi. Endi kirish faqat ilovaning login oqimi (cheklov + TOTP) orqali.
admin.site.login = login_required(admin.site.login)

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
    path("ai/", include("apps.ai_agents.urls")),
    path("", include("apps.core.urls")),
    # Yuklangan fayllar autentifikatsiyadan o'tgan view orqali beriladi
    # (nginx ularni ochiq tarqatmasligi kerak — nginx/default.conf.template ga qarang).
    re_path(r"^media/(?P<path>.*)$", protected_media, name="protected_media"),
]
