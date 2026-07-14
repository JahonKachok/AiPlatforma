from django.contrib import admin

from .models import TelegramEvent, TelegramLinkToken


@admin.register(TelegramLinkToken)
class TelegramLinkTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "token", "created_at", "expires_at", "used_at"]
    readonly_fields = ["token", "created_at"]


@admin.register(TelegramEvent)
class TelegramEventAdmin(admin.ModelAdmin):
    list_display = ["chat_id", "user", "kind", "text", "created_at"]
    list_filter = ["kind"]
    search_fields = ["chat_id", "text"]
    readonly_fields = [f.name for f in TelegramEvent._meta.fields]

    def has_add_permission(self, request):
        return False
