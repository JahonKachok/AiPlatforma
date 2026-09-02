"""Shared read helpers for anything that renders a project as a card or row.

The projects page and the dashboard show the same things about a project —
cover image, progress, members, whether it is late — so the queryset shaping
and the derived fields live here once. In particular there is exactly one
progress algorithm (Project.progress / SubObject.progress); this module only
feeds it prefetched data so it does not fire a query per project.
"""
from datetime import date

from django.db.models import Prefetch

from .models import Project, SubObject

MAX_CARD_AVATARS = 3


def card_queryset(queryset):
    """Add everything the card/row needs in a fixed number of queries.

    ``sub_objects`` is narrowed to root objects and given its own prefetches:
    ``SubObject.progress`` walks ``pod_objects`` and ``disciplines`` with
    ``.all()``, so those hit the prefetch cache instead of the database.
    """
    return queryset.select_related("created_by").prefetch_related(
        "members__user",
        Prefetch(
            "sub_objects",
            queryset=SubObject.objects.filter(parent__isnull=True).prefetch_related(
                "pod_objects__disciplines", "disciplines",
            ),
            to_attr="root_sub_objects",
        ),
    )


def attach_card_fields(projects, today=None):
    """Set the derived attributes the templates read.

    Mirrors ``Project.progress`` but over the prefetched ``root_sub_objects``,
    so the result is identical while costing no extra queries.
    """
    today = today or date.today()
    for project in projects:
        roots = getattr(project, "root_sub_objects", None)
        if roots is None:  # not built by card_queryset — fall back to the model
            project.progress_value = project.progress
        else:
            values = [so.progress for so in roots if so.progress is not None]
            project.progress_value = round(sum(values) / len(values)) if values else None

        members = list(project.members.all())
        project.member_avatars = members[:MAX_CARD_AVATARS]
        project.member_overflow = max(0, len(members) - MAX_CARD_AVATARS)
        project.is_overdue = bool(
            project.deadline
            and project.deadline < today
            and project.status == Project.Status.ACTIVE
        )
    return projects
