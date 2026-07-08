from django import template

register = template.Library()

_STATUS_VARIANT = {
    "active": "success",
    "on_hold": "warning",
    "completed": "default",
    "cancelled": "danger",
}

_STAGE_VARIANT = {
    "concept": "default",
    "preliminary": "info",
    "working_docs": "purple",
    "expertise": "warning",
    "construction": "success",
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
def project_status_badge(status):
    return _BADGE_CLASSES[_STATUS_VARIANT.get(status, "default")]


@register.filter
def project_stage_badge(stage):
    return _BADGE_CLASSES[_STAGE_VARIANT.get(stage, "default")]
