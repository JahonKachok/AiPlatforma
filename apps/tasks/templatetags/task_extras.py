from django import template

register = template.Library()

_STATUS_VARIANT = {
    "new": "info",
    "in_progress": "purple",
    "review": "warning",
    "revision": "danger",
    "approved": "success",
    "completed": "default",
}

_PRIORITY_VARIANT = {
    "low": "default",
    "medium": "info",
    "high": "warning",
    "critical": "danger",
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
def task_status_badge(status):
    return _BADGE_CLASSES[_STATUS_VARIANT.get(status, "default")]


@register.filter
def task_priority_badge(priority):
    return _BADGE_CLASSES[_PRIORITY_VARIANT.get(priority, "default")]
