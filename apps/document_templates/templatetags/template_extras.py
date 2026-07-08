from django import template

register = template.Library()

_TYPE_VARIANT = {"contract": "info", "act": "success", "appendix": "purple", "invoice": "warning", "other": "default"}

_BADGE_CLASSES = {
    "default": "badge badge-default",
    "success": "badge badge-success",
    "warning": "badge badge-warning",
    "danger": "badge badge-danger",
    "info": "badge badge-info",
    "purple": "badge badge-purple",
}


@register.filter
def template_type_badge(template_type):
    return _BADGE_CLASSES[_TYPE_VARIANT.get(template_type, "default")]
