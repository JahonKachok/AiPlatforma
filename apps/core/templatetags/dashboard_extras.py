"""Presentation helpers for the dashboard.

Audit-log rows store a raw action string ("status_changed", "uploaded", ...).
These filters turn that into a readable, translatable label and a colour tone
without touching the log format itself.
"""
from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()

# action -> tone. Anything unknown falls back to "blue", so a new action added
# elsewhere in the app still renders sensibly instead of breaking the page.
_ACTION_TONES = {
    "created": "green",
    "uploaded": "green",
    "new_version": "green",
    "generate_from_template": "purple",
    "updated": "blue",
    "downloaded": "blue",
    "bulk_download": "blue",
    "version_downloaded": "blue",
    "wizard_completed": "blue",
    "status_changed": "amber",
    "quick_approved": "amber",
    "approval_approved": "green",
    "approval_rejected": "red",
    "approval_revision": "amber",
    "deleted": "red",
}

_ACTION_LABELS = {
    "created": _("created"),
    "updated": _("updated"),
    "deleted": _("deleted"),
    "uploaded": _("uploaded a file"),
    "downloaded": _("downloaded a file"),
    "bulk_download": _("downloaded files"),
    "version_downloaded": _("downloaded a version"),
    "new_version": _("added a new version"),
    "status_changed": _("changed the status"),
    "quick_approved": _("approved"),
    "approval_approved": _("approved the document"),
    "approval_rejected": _("rejected the document"),
    "approval_revision": _("sent it back for revision"),
    "generate_from_template": _("generated a document"),
    "wizard_completed": _("completed the setup"),
}


@register.filter
def activity_tone(action):
    return _ACTION_TONES.get(action, "blue")


@register.filter
def activity_label(action):
    """Readable text for a logged action; unknown actions keep their raw name
    (underscores swapped for spaces) rather than being hidden."""
    label = _ACTION_LABELS.get(action)
    if label is not None:
        return label
    return (action or "").replace("_", " ")


@register.filter
def sparkline_points(values, height=28):
    """Turn a list of counts into an SVG polyline over a 100 x `height` box.

    The series is drawn as-is: a flat line means the underlying counts really
    are flat. An empty or single-point series yields "" so the template can
    skip the chart instead of drawing a meaningless dot.
    """
    values = list(values or [])
    if len(values) < 2:
        return ""
    height = float(height)
    top = max(values)
    bottom = min(values)
    span = top - bottom
    step = 100.0 / (len(values) - 1)
    points = []
    for index, value in enumerate(values):
        # A flat series sits on the baseline rather than dividing by zero.
        ratio = 0.5 if span == 0 else (value - bottom) / span
        y = height - (ratio * (height - 2)) - 1
        points.append(f"{index * step:.1f},{y:.1f}")
    return " ".join(points)
