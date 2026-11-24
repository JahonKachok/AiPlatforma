"""Ish vaqtida o'zgartiriladigan integratsiya sozlamalari.

Telegram bot tokeni, AI kalitlari va model nomlari admin paneldan
(core:integration_settings) kiritiladi va bazada shifrlangan holda saqlanadi.
Bazada qiymat bo'lmasa — `.env` / settings dagi qiymat ishlatiladi, ya'ni
eski o'rnatmalar hech narsa o'zgartirmasdan ishlashda davom etadi.

Barcha kod `settings.X` o'rniga `get_config("X")` dan foydalanadi. Qiymatlar
har jarayonda qisqa muddat keshlanadi: veb jarayonda saqlangan o'zgarish
bot va celery jarayonlariga CACHE_TTL soniya ichida yetib boradi.
"""
import base64
import hashlib
import logging
import time
from dataclasses import dataclass, field

from django.conf import settings
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

CACHE_TTL = 30  # soniya


@dataclass(frozen=True)
class ConfigField:
    key: str
    label: str
    group: str
    secret: bool = False
    help_text: str = ""
    choices: tuple = field(default_factory=tuple)


FIELDS = (
    ConfigField("TELEGRAM_BOT_TOKEN", _("Bot token"), "telegram", secret=True,
                help_text=_("From @BotFather. The bot restarts with the new token within a minute.")),
    ConfigField("TELEGRAM_BOT_USERNAME", _("Bot username"), "telegram",
                help_text=_("Without @, e.g. gastec_bot")),
    ConfigField("GEMINI_API_KEY", _("Gemini API key"), "ai", secret=True,
                help_text="https://aistudio.google.com"),
    ConfigField("ANTHROPIC_API_KEY", _("Claude (Anthropic) API key"), "ai", secret=True,
                help_text="https://console.anthropic.com"),
    ConfigField("AI_PROVIDER", _("AI provider"), "ai",
                help_text=_("Automatic: Gemini if its key is set, otherwise Claude."),
                choices=(("", _("Automatic")), ("gemini", "Gemini"), ("anthropic", "Claude"))),
    ConfigField("GEMINI_MODEL", _("Gemini model"), "ai"),
    ConfigField("GEMINI_FALLBACK_MODEL", _("Gemini fallback model"), "ai"),
    ConfigField("AI_MODEL", _("Claude model"), "ai"),
    # Devbot (deploy/devbot) — Telegram orqali platforma kodini o'zgartiruvchi
    # bot. U serverda alohida ishlaydi va bu qiymatlarni `manage.py
    # devbot_config` orqali o'qiydi. Buyruqni faqat Telegram'i ulangan
    # adminlar bera oladi.
    ConfigField("DEVBOT_TELEGRAM_TOKEN", _("Devbot token"), "devbot", secret=True,
                help_text=_("A separate bot from @BotFather (not the main bot's token). "
                            "The devbot restarts with the new token within a minute.")),
    ConfigField("DEVBOT_TELEGRAM_USERNAME", _("Devbot username"), "devbot",
                help_text=_("Without @, e.g. aiplatforma_dev_bot")),
    ConfigField("DEVBOT_ANTHROPIC_API_KEY", _("Devbot Claude (Anthropic) API key"), "devbot", secret=True,
                help_text=_("Used by Claude Code to change the code. If empty, the Claude key above is used.")),
    ConfigField("DEVBOT_CLAUDE_MODEL", _("Devbot Claude model"), "devbot",
                help_text=_("Empty: Claude Code default.")),
)
FIELDS_BY_KEY = {f.key: f for f in FIELDS}

_cache: dict[str, str] = {}
_cache_loaded_at = 0.0


# --- shifrlash ---------------------------------------------------------------

def _fernet():
    from cryptography.fernet import Fernet

    digest = hashlib.sha256(f"integration-settings:{settings.SECRET_KEY}".encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str) -> str:
    from cryptography.fernet import InvalidToken

    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        # SECRET_KEY almashtirilgan bo'lsa eski qiymatni ochib bo'lmaydi —
        # .env qiymatiga qaytamiz, admin kalitni qayta kiritishi kerak.
        logger.warning("Integratsiya sozlamasini ochib bo'lmadi (SECRET_KEY o'zgarganmi?)")
        return ""


# --- o'qish / yozish -----------------------------------------------------------

def _load_db_values() -> dict[str, str]:
    from django.db import DatabaseError

    from .models import IntegrationSetting

    try:
        rows = list(IntegrationSetting.objects.filter(key__in=FIELDS_BY_KEY))
    except DatabaseError:
        # Migratsiya hali qo'llanmagan — faqat .env ishlaydi.
        return {}
    return {row.key: decrypt(row.value_encrypted) for row in rows if row.value_encrypted}


def db_values(refresh: bool = False) -> dict[str, str]:
    global _cache, _cache_loaded_at
    if refresh or time.monotonic() - _cache_loaded_at > CACHE_TTL:
        _cache = _load_db_values()
        _cache_loaded_at = time.monotonic()
    return _cache


def get_config(key: str) -> str:
    """Bazadagi qiymat (bo'lmasa — settings/.env dagi qiymat)."""
    value = db_values().get(key)
    if value:
        return value
    return getattr(settings, key, "") or ""


def env_value(key: str) -> str:
    return getattr(settings, key, "") or ""


def set_config(key: str, value: str, user=None) -> None:
    """Qiymatni saqlaydi; bo'sh qiymat bazadagi yozuvni o'chiradi (.env ga qaytadi)."""
    from .models import IntegrationSetting

    if key not in FIELDS_BY_KEY:
        raise KeyError(key)
    value = (value or "").strip()
    if value:
        IntegrationSetting.objects.update_or_create(
            key=key, defaults={"value_encrypted": encrypt(value), "updated_by": user},
        )
    else:
        IntegrationSetting.objects.filter(key=key).delete()
    invalidate()


def invalidate() -> None:
    global _cache_loaded_at
    _cache_loaded_at = 0.0


def mask(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "•" * len(value)
    return "•" * 8 + value[-4:]
