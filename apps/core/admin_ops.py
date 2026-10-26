import re
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import User

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
