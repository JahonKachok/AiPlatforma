"""Arxivarius: hujjat reviziyalarini Google Drive'ga tartib bilan joylash.

Drive tuzilmasi: <ildiz>/<Loyiha>/<Obyekt>/<Pod-obyekt>/<Intizom>/<fayl>.
Hujjatning yangi reviziyasi papkaga tushadi, oldingilari shu papka ichidagi
«Old» papkasiga ko'chiriladi. Fayl nomlari o'zgartirilmaydi.

Reviziyalar reyestri — DocumentVersion (revision, drive_status, ...).
"""
import logging

import requests
from django.db import transaction
from django.utils import timezone

from apps.core.runtime_config import get_config

from . import drive
from .models import Document, DocumentVersion, DriveFolder, DriveStatus
from .services import file_basename, folder_parts

logger = logging.getLogger(__name__)


def _path_key(root, parts):
    return "/".join([root, *(p.replace("/", "∕") for p in parts)])


def drive_folder_for(document, *, old=False):
    """Hujjat papkasining Drive ID'si (yo'q bo'lsa yaratiladi, keshlanadi)."""
    root = drive.root_folder_id()
    parts = folder_parts(document) + ([drive.OLD_FOLDER] if old else [])
    parent = root
    for i, name in enumerate(parts, start=1):
        key = _path_key(root, parts[:i])
        cached = DriveFolder.objects.filter(path=key).first()
        if cached:
            parent = cached.folder_id
            continue
        parent = drive.ensure_folder(parent, name)
        DriveFolder.objects.update_or_create(path=key, defaults={"folder_id": parent})
    return parent


def _forget_folders(document):
    """Kesh eskirgan bo'lishi mumkin (papka Drive'da o'chirilgan) — keyingi
    urinishda papkalar qaytadan qidiriladi."""
    root = drive.root_folder_id()
    DriveFolder.objects.filter(path__startswith=_path_key(root, folder_parts(document)[:1])).delete()


def open_file(obj):
    """Hujjat yoki versiya faylini o'qish uchun ochadi: avval server, u yerda
    bo'lmasa (GOOGLE_DRIVE_DELETE_LOCAL) — Drive'dan."""
    try:
        return obj.file.open("rb")
    except FileNotFoundError:
        if obj.drive_file_id and drive.is_configured():
            return drive.download(obj.drive_file_id)
        raise


def is_latest(version):
    return not DocumentVersion.objects.filter(document_id=version.document_id, revision__gt=version.revision).exists()


def sync_version(version):
    """Reviziyani Drive'ga yuklaydi. True — yuklandi (yoki avval yuklangan)."""
    if version.drive_status == DriveStatus.SYNCED and version.drive_file_id:
        return True
    if not drive.is_configured() or not version.file:
        return False
    document = version.document
    latest = is_latest(version)
    try:
        folder = drive_folder_for(document)
        # Kechikib yuklanayotgan eski reviziya to'g'ridan-to'g'ri Old'ga tushadi.
        target = folder if latest else drive_folder_for(document, old=True)
        with open_file(version) as fh:
            file_id = drive.upload(
                target, file_basename(version), fh, document.mime_type or "",
                description=f"{document.name} · rev {version.revision}",
            )
    except (drive.DriveError, FileNotFoundError, requests.RequestException) as exc:
        logger.warning("Drive sync failed for version %s: %s", version.pk, exc)
        _forget_folders(document)
        DocumentVersion.objects.filter(pk=version.pk).update(drive_status=DriveStatus.ERROR, drive_error=str(exc)[:500])
        return False

    DocumentVersion.objects.filter(pk=version.pk).update(
        drive_status=DriveStatus.SYNCED, drive_file_id=file_id, drive_folder_id=target,
        drive_error="", drive_synced_at=timezone.now(), in_old_folder=not latest,
    )
    if latest:
        Document.objects.filter(pk=document.pk).update(drive_file_id=file_id, drive_folder_id=folder)
        _archive_previous(version, folder)
    _maybe_delete_local(version)
    return True


def _archive_previous(version, folder):
    """Oldingi reviziyalarni papkadagi «Old» ichiga ko'chiradi."""
    previous = DocumentVersion.objects.filter(
        document_id=version.document_id, revision__lt=version.revision, in_old_folder=False,
    ).exclude(drive_file_id="")
    if not previous.exists():
        return
    try:
        old_folder = drive_folder_for(version.document, old=True)
        for prev in previous:
            drive.move(prev.drive_file_id, old_folder, prev.drive_folder_id or folder)
            DocumentVersion.objects.filter(pk=prev.pk).update(in_old_folder=True, drive_folder_id=old_folder)
    except (drive.DriveError, requests.RequestException) as exc:
        # Yangi reviziya joyida — eskisini keyingi sinxronlashda ko'chiramiz.
        logger.warning("Moving old revisions to Old failed for %s: %s", version.document_id, exc)


def _maybe_delete_local(version):
    """Server xotirasini tejash: Drive'ga tushgan faylning lokal nusxasini o'chirish
    (admin panelda yoqiladi). Yozuv saqlanadi, fayl keyin Drive'dan o'qiladi."""
    if get_config("GOOGLE_DRIVE_DELETE_LOCAL") != "1" or not version.file:
        return
    name = version.file.name
    # Shu fayl boshqa, hali Drive'ga tushmagan versiyada ham ishlatilayotgan bo'lsa — qoldiramiz.
    if DocumentVersion.objects.filter(file=name).exclude(drive_status=DriveStatus.SYNCED).exists():
        return
    version.file.storage.delete(name)


def queue_sync(version):
    """Tranzaksiya yakunlangach Drive'ga yuklashni navbatga qo'yadi."""
    from .tasks import sync_version_to_drive

    pk = str(version.pk)
    transaction.on_commit(lambda: sync_version_to_drive.delay(pk))


def find_same_file(project, section, filename):
    """Shu loyiha/bo'limda xuddi shu nomli fayl bormi — bo'lsa, yangi yuklash
    uning keyingi reviziyasi hisoblanadi (dublikat hujjat yaratilmaydi)."""
    if not filename:
        return None
    return (
        Document.objects.filter(project=project, section=section, original_name__iexact=filename)
        .order_by("-updated_at").first()
    )


def next_version_label(current):
    major = current.split(".")[0] if "." in current else current
    try:
        minor = int(current.split(".")[1]) + 1
    except (IndexError, ValueError):
        minor = 1
    return f"{major}.{minor}"


def add_revision(document, uploaded, user, notes=None):
    """Hujjatga yangi reviziya qo'shadi. Fayl omborga bir marta yoziladi —
    hujjat yangi versiyaning faylini ko'rsatadi."""
    label = next_version_label(document.version)
    version = DocumentVersion.objects.create(
        document=document, version_number=label, file=uploaded,
        file_size=uploaded.size, uploaded_by=user, notes=notes,
    )
    document.file = version.file.name
    document.original_name = version.original_name
    document.version = label
    document.file_size = uploaded.size
    document.mime_type = getattr(uploaded, "content_type", "") or document.mime_type
    document.save()
    return version
