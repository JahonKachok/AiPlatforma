from django import template

register = template.Library()

_STATUS_VARIANT = {"pending": "warning", "confirmed": "success", "cancelled": "danger"}
_TYPE_VARIANT = {"income": "success", "expense": "danger", "advance": "info", "payment": "purple"}

_BADGE_CLASSES = {
    "default": "badge badge-default",
    "success": "badge badge-success",
    "warning": "badge badge-warning",
    "danger": "badge badge-danger",
    "info": "badge badge-info",
    "purple": "badge badge-purple",
}


@register.filter
def record_status_badge(status):
    return _BADGE_CLASSES[_STATUS_VARIANT.get(status, "default")]


@register.filter
def record_type_badge(record_type):
    return _BADGE_CLASSES[_TYPE_VARIANT.get(record_type, "default")]
