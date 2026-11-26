"""Google Drive v3 bilan ishlash (REST, google-auth orqali).

Kirish — service account: uning JSON kaliti admin paneldagi
GOOGLE_DRIVE_CREDENTIALS maydonida, ildiz papka — GOOGLE_DRIVE_ROOT_FOLDER_ID.
Service account'ning o'z diski (kvotasi) yo'q, shuning uchun ildiz papka
Shared Drive ichida bo'lishi yoki service account'ga «Muharrir» sifatida
ulashilgan bo'lishi kerak. Barcha so'rovlar supportsAllDrives bilan.

Kalit o'rnatilmagan bo'lsa `is_configured()` False — platforma Drive'siz
ishlayveradi, fayllar keyin `manage.py drive_sync` bilan yuklanadi.
"""
import json
import logging
import tempfile

from apps.core.runtime_config import get_config

logger = logging.getLogger(__name__)

API = "https://www.googleapis.com/drive/v3"
UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
FOLDER_MIME = "application/vnd.google-apps.folder"
SCOPES = ["https://www.googleapis.com/auth/drive"]
TIMEOUT = 120
OLD_FOLDER = "Old"


class DriveError(Exception):
    pass


def is_configured() -> bool:
    return bool(get_config("GOOGLE_DRIVE_CREDENTIALS") and get_config("GOOGLE_DRIVE_ROOT_FOLDER_ID"))


def root_folder_id() -> str:
    return get_config("GOOGLE_DRIVE_ROOT_FOLDER_ID")


def parse_credentials(raw: str) -> dict:
    """Service account JSON'ini tekshiradi (admin panel validatsiyasi ham shuni ishlatadi)."""
    try:
        info = json.loads(raw)
    except ValueError as exc:
        raise DriveError("not JSON") from exc
    if not isinstance(info, dict) or info.get("type") != "service_account" \
            or not info.get("client_email") or not info.get("private_key"):
        raise DriveError("not a service account key")
    return info


_session_cache = {"raw": None, "session": None}


def _session():
    raw = get_config("GOOGLE_DRIVE_CREDENTIALS")
    if not raw:
        raise DriveError("Google Drive is not configured")
    if _session_cache["raw"] != raw:
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        creds = service_account.Credentials.from_service_account_info(parse_credentials(raw), scopes=SCOPES)
        _session_cache.update(raw=raw, session=AuthorizedSession(creds))
    return _session_cache["session"]


def _check(response):
    if response.status_code >= 400:
        raise DriveError(f"Drive API {response.status_code}: {response.text[:300]}")
    return response


def _q(value: str) -> str:
    """Drive qidiruv so'rovi uchun satrni ekranlash."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


_ALL = {"supportsAllDrives": "true"}


def find_folder(parent_id: str, name: str) -> str | None:
    params = {
        "q": f"name = '{_q(name)}' and '{_q(parent_id)}' in parents and mimeType = '{FOLDER_MIME}' and trashed = false",
        "fields": "files(id)", "pageSize": 1, "includeItemsFromAllDrives": "true", "corpora": "allDrives", **_ALL,
    }
    files = _check(_session().get(f"{API}/files", params=params, timeout=TIMEOUT)).json().get("files", [])
    return files[0]["id"] if files else None


def create_folder(parent_id: str, name: str) -> str:
    body = {"name": name, "mimeType": FOLDER_MIME, "parents": [parent_id]}
    response = _session().post(f"{API}/files", params={"fields": "id", **_ALL}, json=body, timeout=TIMEOUT)
    return _check(response).json()["id"]


def ensure_folder(parent_id: str, name: str) -> str:
    return find_folder(parent_id, name) or create_folder(parent_id, name)


def upload(folder_id: str, name: str, fileobj, mime_type: str = "", description: str = "") -> str:
    """Faylni resumable so'rov bilan yuklaydi (katta DWG'lar ham), fayl ID'sini qaytaradi."""
    session = _session()
    meta = {"name": name, "parents": [folder_id]}
    if description:
        meta["description"] = description
    start = _check(session.post(
        f"{UPLOAD_API}/files", params={"uploadType": "resumable", "fields": "id", **_ALL},
        json=meta, headers={"X-Upload-Content-Type": mime_type or "application/octet-stream"}, timeout=TIMEOUT,
    ))
    location = start.headers["Location"]
    response = _check(session.put(location, data=fileobj, timeout=TIMEOUT * 5))
    return response.json()["id"]


def move(file_id: str, new_parent: str, old_parent: str) -> None:
    params = {"addParents": new_parent, "removeParents": old_parent, "fields": "id", **_ALL}
    _check(_session().patch(f"{API}/files/{file_id}", params=params, json={}, timeout=TIMEOUT))


def download(file_id: str):
    """Fayl mazmunini vaqtinchalik faylga (boshiga qaytarilgan) yuklab oladi."""
    response = _check(_session().get(
        f"{API}/files/{file_id}", params={"alt": "media", **_ALL}, stream=True, timeout=TIMEOUT,
    ))
    out = tempfile.SpooledTemporaryFile(max_size=20 * 1024 * 1024)
    for chunk in response.iter_content(1024 * 1024):
        out.write(chunk)
    out.seek(0)
    return out


def file_url(file_id: str) -> str:
    return f"https://drive.google.com/file/d/{file_id}/view"


def folder_url(folder_id: str) -> str:
    return f"https://drive.google.com/drive/folders/{folder_id}"
