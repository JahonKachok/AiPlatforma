from django import template

register = template.Library()

_STATUS_VARIANT = {
    "draft": "default",
    "review": "warning",
    "approved": "success",
    "rejected": "danger",
    "archived": "purple",
}

_APPROVAL_VARIANT = {
    "pending": "warning",
    "approved": "success",
    "rejected": "danger",
    "revision": "info",
}

_BADGE_CLASSES = {
    "default": "badge badge-default",
    "success": "badge badge-success",
    "warning": "badge badge-warning",
    "danger": "badge badge-danger",
    "info": "badge badge-info",
    "purple": "badge badge-purple",
}


@register.filter
def document_status_badge(status):
    return _BADGE_CLASSES[_STATUS_VARIANT.get(status, "default")]


@register.filter
def approval_status_badge(status):
    return _BADGE_CLASSES[_APPROVAL_VARIANT.get(status, "default")]


@register.filter
def filesizeformat_short(num_bytes):
    try:
        num = float(num_bytes)
    except (TypeError, ValueError):
        return "—"
    for unit in ["B", "KB", "MB", "GB"]:
        if num < 1024:
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"


@register.filter
def folder_path(document):
    """«Loyiha / Obyekt / Pod-obyekt / Intizom» — hujjat qaysi papkada turgani."""
    from apps.documents.services import folder_parts

    return " / ".join(folder_parts(document))


@register.filter
def drive_folder_url(folder_id):
    from apps.documents.drive import folder_url

    return folder_url(folder_id) if folder_id else ""


@register.filter
def drive_file_url(file_id):
    from apps.documents.drive import file_url

    return file_url(file_id) if file_id else ""
