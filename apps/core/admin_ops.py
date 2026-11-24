import re
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User

from . import devbot, runtime_config
from .permissions import role_required

# Backup — butun bazaning nusxasi: parol xeshlari, TOTP sirlari, barcha
# moliyaviy yozuvlar. Shuning uchun u bilan faqat admin ishlaydi.
MANAGE_ROLES = (User.Role.ADMIN,)
DELETE_ROLES = (User.Role.ADMIN,)

BACKUP_DIR = settings.BASE_DIR / "backups"
_BACKUP_NAME_RE = re.compile(r"^backup_\d{8}_\d{6}\.zip$")


def _backup_path(filename):
    """Faqat o'zimiz yaratgan nomdagi fayllar — boshqa hech narsa backups/
    katalogidan berilmaydi yoki o'chirilmaydi."""
    if not _BACKUP_NAME_RE.match(filename):
        raise Http404
    path = BACKUP_DIR / filename
    if not path.is_file():
        raise Http404
    return path


@role_required(*MANAGE_ROLES)
def backup_list(request):
    BACKUP_DIR.mkdir(exist_ok=True)
    if request.method == "POST":
        _create_backup()
        messages.success(request, _("Backup created."))
        return redirect("core:backup_list")

    backups = sorted(BACKUP_DIR.glob("backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    entries = [
        {"name": p.name, "size_mb": round(p.stat().st_size / 1_000_000, 2), "mtime": p.stat().st_mtime}
        for p in backups[:20]
    ]
    return render(request, "core/backup_list.html", {
        "backups": entries,
        "can_delete": request.user.is_superuser or request.user.role in DELETE_ROLES,
    })


def _create_backup():
    from datetime import datetime

    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = BACKUP_DIR / f"backup_{timestamp}.zip"
    db_path = settings.BASE_DIR / "db.sqlite3"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if db_path.exists():
            zf.write(db_path, arcname="db.sqlite3")
        # Docker'da baza Postgres: uning nusxasini db-backup konteyneri
        # backups/db/ ga yozadi (deploy/db-backup.sh) — eng oxirgisi qo'shiladi.
        dumps = sorted((BACKUP_DIR / "db").glob("db_*.dump"), key=lambda p: p.stat().st_mtime)
        if dumps:
            zf.write(dumps[-1], arcname=f"db/{dumps[-1].name}")
        media_root = Path(settings.MEDIA_ROOT)
        if media_root.exists():
            for file_path in media_root.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, arcname=str(file_path.relative_to(media_root.parent)))
    return zip_path


@role_required(*MANAGE_ROLES)
def backup_download(request, filename):
    path = _backup_path(filename)
    return FileResponse(open(path, "rb"), as_attachment=True, filename=filename)


@role_required(*DELETE_ROLES)
def backup_delete(request, filename):
    path = _backup_path(filename)
    if request.method == "POST":
        path.unlink()
        messages.success(request, _("Backup deleted."))
    return redirect("core:backup_list")


# ---------------------------------------------------------------------------
# Integratsiya sozlamalari (Telegram bot tokeni, AI kalitlari)
# ---------------------------------------------------------------------------

_TELEGRAM_TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{30,}$")


def _validate_integration(key, value):
    if not value:
        return None
    if key in ("TELEGRAM_BOT_TOKEN", "DEVBOT_TELEGRAM_TOKEN") and not _TELEGRAM_TOKEN_RE.match(value):
        return _("Invalid bot token format (expected 123456:ABC...).")
    if key in ("TELEGRAM_BOT_USERNAME", "DEVBOT_TELEGRAM_USERNAME") and not re.match(r"^@?[A-Za-z0-9_]{5,32}$", value):
        return _("Invalid bot username.")
    # Bitta tokenni ikki jarayon polling qila olmaydi — botlar bir-birini
    # "409 Conflict" bilan to'xtatib qo'yadi.
    other = {"TELEGRAM_BOT_TOKEN": "DEVBOT_TELEGRAM_TOKEN", "DEVBOT_TELEGRAM_TOKEN": "TELEGRAM_BOT_TOKEN"}.get(key)
    if other and value == runtime_config.get_config(other):
        return _("The devbot needs its own bot token, different from the main bot.")
    field = runtime_config.FIELDS_BY_KEY[key]
    if field.choices and value not in {c[0] for c in field.choices}:
        return _("Invalid choice.")
    if any(ch.isspace() for ch in value):
        return _("Value must not contain spaces.")
    return None


@role_required(*MANAGE_ROLES)
def integration_settings(request):
    """Tokenlar sahifasi. Maxfiy maydonlar hech qachon to'liq ko'rsatilmaydi:
    bo'sh qoldirilsa — eski qiymat saqlanadi, "Tozalash" belgilansa —
    bazadagi qiymat o'chadi va .env dagisi ishlatiladi."""
    db_values = runtime_config.db_values(refresh=True)
    errors = {}

    if request.method == "POST":
        changes = {}
        for field in runtime_config.FIELDS:
            key = field.key
            if request.POST.get(f"clear_{key}"):
                if key in db_values:
                    changes[key] = ""
                continue
            value = request.POST.get(key, "").strip()
            if key in ("TELEGRAM_BOT_USERNAME", "DEVBOT_TELEGRAM_USERNAME"):
                value = value.lstrip("@")
            if field.secret and not value:
                continue  # bo'sh — o'zgarishsiz
            if value == db_values.get(key, ""):
                continue
            error = _validate_integration(key, value)
            if error:
                errors[key] = error
            else:
                changes[key] = value
        if not errors:
            for key, value in changes.items():
                runtime_config.set_config(key, value, user=request.user)
            if changes:
                messages.success(request, _("Settings saved."))
            return redirect("core:integration_settings")

    groups = {"telegram": [], "ai": [], "devbot": []}
    for field in runtime_config.FIELDS:
        db_value = db_values.get(field.key, "")
        env_value = runtime_config.env_value(field.key)
        effective = db_value or env_value
        groups[field.group].append({
            "field": field,
            "db_value": "" if field.secret else db_value,
            "source": "db" if db_value else ("env" if env_value else ""),
            "display": runtime_config.mask(effective) if field.secret else effective,
            "posted": "" if field.secret else request.POST.get(
                field.key, db_value or (env_value if field.choices else "")),
            "error": errors.get(field.key),
        })
    return render(request, "core/integration_settings.html", {
        "telegram_fields": groups["telegram"],
        "ai_fields": groups["ai"],
        "devbot_fields": groups["devbot"],
        "devbot_status": devbot.status(),
        "devbot_admins": devbot.allowed_admins(),
        "devbot_username": runtime_config.get_config("DEVBOT_TELEGRAM_USERNAME"),
    })
