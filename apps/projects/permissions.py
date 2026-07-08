from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User


def visible_projects_for(user):
    """Mirrors the previous API's visibility rule: admin/manager see
    everything, everyone else only sees projects they're an active member of."""
    from .models import Project

    if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.MANAGER):
        return Project.objects.all()
    return Project.objects.filter(
        Q(members__user=user)
        & (Q(members__expires_at__isnull=True) | Q(members__expires_at__gt=timezone.now()))
    ).distinct()


def can_edit_project(user, project):
    if user.is_superuser or user.role in (User.Role.ADMIN, User.Role.MANAGER):
        return True
    return project.members.filter(
        user=user, can_edit=True
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    ).exists()


def can_create_project(user):
    return user.is_superuser or user.role in (User.Role.ADMIN, User.Role.MANAGER, User.Role.GIP)


def ensure_project_member(project, user):
    """Assigning someone a task/document review/etc. on a project implicitly
    grants them at least view access to it — otherwise they couldn't see the
    work they were just assigned. Mirrors project_create's auto-add-creator
    behavior for any other assignment entry point."""
    from .models import ProjectMember

    if user is None:
        return
    ProjectMember.objects.get_or_create(project=project, user=user)
