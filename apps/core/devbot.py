"""Devbot (deploy/devbot) bilan platforma o'rtasidagi ko'prik.

Devbot serverda Docker'dan tashqarida ishlaydi va sozlamalarni
`docker exec <web> python manage.py devbot_config` orqali oladi. Shu bilan
birga u o'z holatini (heartbeat) yuboradi — integratsiya sahifasida
"ishlayapti / javob bermayapti" shundan ko'rsatiladi.
"""
import time

from django.core.cache import cache
from django.db.models import Q

from apps.accounts.models import User

from .runtime_config import get_config

HEARTBEAT_KEY = "devbot:heartbeat"
HEARTBEAT_TTL = 24 * 3600
ONLINE_SECONDS = 120


def allowed_admins():
    """Devbot'ga buyruq bera oladiganlar: Telegram'i ulangan faol adminlar."""
    return list(
        User.objects.filter(Q(role=User.Role.ADMIN) | Q(is_superuser=True), is_active=True)
        .exclude(telegram_chat_id__isnull=True).exclude(telegram_chat_id="")
        .order_by("full_name")
    )


def config():
    """Devbot uchun sozlamalar (maxfiy qiymatlar ochiq holda — faqat
    serverdagi devbot jarayoni docker exec orqali o'qiydi)."""
    admin_ids = []
    for user in allowed_admins():
        try:
            admin_ids.append(int(user.telegram_chat_id))
        except ValueError:
            continue
    return {
        "telegram_token": get_config("DEVBOT_TELEGRAM_TOKEN"),
        "telegram_username": get_config("DEVBOT_TELEGRAM_USERNAME"),
        "anthropic_api_key": get_config("DEVBOT_ANTHROPIC_API_KEY") or get_config("ANTHROPIC_API_KEY"),
        "claude_model": get_config("DEVBOT_CLAUDE_MODEL"),
        "admin_ids": admin_ids,
    }


def record_heartbeat(data: dict):
    cache.set(HEARTBEAT_KEY, {**data, "at": time.time()}, HEARTBEAT_TTL)


def status():
    beat = cache.get(HEARTBEAT_KEY)
    if not beat:
        return {"state": "never"}
    age = int(time.time() - beat.get("at", 0))
    return {
        **beat,
        "age": age,
        "state": ("busy" if beat.get("busy") else "online") if age <= ONLINE_SECONDS else "offline",
    }
