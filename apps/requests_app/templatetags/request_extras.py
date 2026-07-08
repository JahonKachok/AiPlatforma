from django import template

register = template.Library()

_STATUS_VARIANT = {"open": "info", "in_progress": "purple", "resolved": "success", "closed": "default"}
_PRIORITY_VARIANT = {"low": "default", "medium": "info", "high": "danger"}

_BADGE_CLASSES = {
    "default": "badge badge-default",
    "success": "badge badge-success",
    "warning": "badge badge-warning",
    "danger": "badge badge-danger",
    "info": "badge badge-info",
    "purple": "badge badge-purple",
}


@register.filter
def request_status_badge(status):
    return _BADGE_CLASSES[_STATUS_VARIANT.get(status, "default")]


@register.filter
def request_priority_badge(priority):
    return _BADGE_CLASSES[_PRIORITY_VARIANT.get(priority, "default")]
