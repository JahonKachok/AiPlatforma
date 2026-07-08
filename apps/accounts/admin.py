from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import LoginJournal, NotificationPreference, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = ["email", "full_name", "role", "is_active", "is_staff"]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["email", "full_name"]
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("full_name", "role", "department", "phone", "avatar", "telegram_chat_id")}),
        ("Security", {"fields": ("is_verified", "totp_secret", "two_factor_enabled")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "role", "password1", "password2"),
        }),
    )
    readonly_fields = ["created_at", "updated_at", "last_login"]


@admin.register(LoginJournal)
class LoginJournalAdmin(admin.ModelAdmin):
    list_display = ["user", "status", "ip_address", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__email"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user"]
