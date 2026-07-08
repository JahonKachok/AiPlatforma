from django import template
from django.utils import timezone

register = template.Library()

_AVATAR_PALETTE = [
    "#f87171", "#fb923c", "#fbbf24", "#4ade80",
    "#22d3ee", "#60a5fa", "#a78bfa", "#f472b6",
]

_BADGE_CLASSES = {
    "default": "badge badge-default",
    "success": "badge badge-success",
    "warning": "badge badge-warning",
    "danger": "badge badge-danger",
    "info": "badge badge-info",
    "purple": "badge badge-purple",
}


@register.filter
def initials(name):
    if not name:
        return "?"
    parts = str(name).split()
    letters = "".join(p[0] for p in parts[:2] if p)
    return letters.upper() or "?"


@register.filter
def avatar_color(name):
    if not name:
        return _AVATAR_PALETTE[0]
    total = sum(ord(ch) for ch in str(name))
    return _AVATAR_PALETTE[total % len(_AVATAR_PALETTE)]


@register.filter
def money(value):
    """1250000 -> '1 250 000' (matches the previous app's space-separated
    thousands formatting used in generated contracts)."""
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return value
    return f"{n:,}".replace(",", " ")


@register.filter
def millions(value):
    try:
        return f"{float(value) / 1_000_000:.1f}"
    except (TypeError, ValueError):
        return value


@register.filter
def is_overdue(deadline):
    if not deadline:
        return False
    now = timezone.now()
    if timezone.is_naive(deadline):
        now = timezone.make_naive(now)
    return deadline < now


@register.filter
def badge(variant):
    return _BADGE_CLASSES.get(variant, _BADGE_CLASSES["default"])


@register.filter
def get_item(mapping, key):
    if not mapping:
        return []
    return mapping.get(key, [])
