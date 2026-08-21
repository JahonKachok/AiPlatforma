from apps.accounts.models import User

_PRIVILEGED_ROLES = {User.Role.ADMIN, User.Role.MANAGER}

_EXECUTOR_TRANSITIONS = {
    "new": {"in_progress"},
    "in_progress": {"review"},
    "revision": {"review"},
}


def is_privileged(user):
    return user.is_superuser or user.role in _PRIVILEGED_ROLES


def resolve_reviewer(task):
    """The GIP responsible for the task's section (falling back to the
    section's sub-object) checks work once it reaches 'review'."""
    if task.section_id:
        if task.section.gip_id:
            return task.section.gip
        sub_object = task.section.sub_object
        if sub_object and sub_object.gip_id:
            return sub_object.gip
    return None


def can_change_task_status(user, task, new_status):
    if new_status == task.status:
        return True
    if is_privileged(user):
        return True
    reviewer = resolve_reviewer(task)
    if reviewer is not None and reviewer.id == user.id:
        return True
    if task.assignee_id == user.id:
        return new_status in _EXECUTOR_TRANSITIONS.get(task.status, set())
    return False


def allowed_status_targets(user, task):
    from .models import Task

    return {v for v, _l in Task.Status.choices if v != task.status and can_change_task_status(user, task, v)}
