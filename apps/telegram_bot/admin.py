from django.contrib import admin

from .models import TelegramLinkToken


@admin.register(TelegramLinkToken)
class TelegramLinkTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "token", "created_at", "expires_at", "used_at"]
    readonly_fields = ["token", "created_at"]
