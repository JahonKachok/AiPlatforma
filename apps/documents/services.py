import re
import tempfile
import zipfile


def resolve_project_gip(project):
    """The GIP attached to the project itself — the person who signs work off.
    Ordered by join date so a project with several GIPs always resolves to the
    same one rather than whichever the database happens to return first."""
    member = (
        project.members.filter(role_in_project="gip")
        .select_related("user").order_by("joined_at").first()
    )
    return member.user if member else None


def resolve_gip_reviewer(sub_object, project):
    """Walk up from the sub-object (a pod object's own GIP takes priority over
    its parent object's) to find who should review work submitted on it; falls
    back to the project's GIP member if neither the object nor its parent has one."""
    candidate = sub_object
    while candidate is not None:
        if candidate.gip_id:
            return candidate.gip
        candidate = candidate.parent
    return resolve_project_gip(project)


# --- Joylashuv, ZIP va Telegram'ga ulashish -------------------------------

# Telegram Bot API yuklash chegarasi (bot fayl yuborishda 50 MB dan oshirolmaydi).
TELEGRAM_FILE_LIMIT = 50 * 1024 * 1024
_UNSAFE = re.compile(r'[\/:*?"<>|\x00-\x1f]+')


def folder_parts(document):
    """Hujjat joylashuvi: [loyiha, obyekt, pod-obyekt, intizom] (bo'sh
    qismlarsiz). ZIP ichidagi papkalar va keyin Google Drive papkalari shu
    tuzilmada bo'ladi."""
    parts = [document.project.name]
    section = document.section
    if section is not None:
        sub = section.sub_object
        if sub is not None:
            if sub.parent_id:
                parts.append(sub.parent.name)
            parts.append(sub.name)
        parts.append(section.discipline.code)
    return parts


def file_basename(obj):
    """Hujjat yoki versiya faylining asl nomi (eski yozuvlarda — saqlangan nom)."""
    return obj.original_name or obj.file.name.rsplit("/", 1)[-1]


def _safe(part):
    return _UNSAFE.sub("_", part).strip(" .") or "_"


def build_zip(documents):
    """Hujjat fayllarini Obyekt/Intizom papkalari bilan ZIP'ga yig'adi.

    Fayl nomlari o'zgartirilmaydi; faqat bir papkada nom takrorlansa
    « (2)» qo'shiladi. Natija — boshiga qaytarilgan vaqtinchalik fayl
    (katta arxiv xotirani to'ldirmasligi uchun diskka tushadi) va
    qo'shilgan hujjatlar ro'yxati."""
    out = tempfile.SpooledTemporaryFile(max_size=20 * 1024 * 1024)
    added, used = [], set()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for document in documents:
            if not document.file:
                continue
            folder = "/".join(_safe(p) for p in folder_parts(document))
            name = file_basename(document)
            stem, dot, ext = name.rpartition(".")
            path, n = f"{folder}/{name}", 1
            while path.lower() in used:
                n += 1
                path = f"{folder}/{stem} ({n}).{ext}" if dot else f"{folder}/{name} ({n})"
            from .archivist import open_file  # aylanma import: archivist -> services

            try:
                with open_file(document) as src, zf.open(path, "w") as dst:
                    for chunk in iter(lambda: src.read(1024 * 1024), b""):
                        dst.write(chunk)
            except FileNotFoundError:
                continue
            used.add(path.lower())
            added.append(document)
    out.seek(0)
    return out, added


def zip_filename(documents):
    """Bitta loyiha bo'lsa arxiv loyiha nomi bilan, aks holda «documents.zip»."""
    names = {d.project.name for d in documents}
    return f"{_safe(names.pop())}.zip" if len(names) == 1 else "documents.zip"
