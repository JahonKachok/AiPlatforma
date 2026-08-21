from django.utils.translation import gettext, gettext_lazy as _


def ensure_discipline_task(assignment, actor):
    """Assigning a specialist to a sub-object's discipline hands them the work
    itself, not just the label: a task on the matching
    Project -> Object -> Sub-object -> Discipline section.

    Returns the new Task, or None when there is nobody to assign it to or that
    person already has a task on this section (so pressing "Assign" again, or
    only changing the deadline, never piles up duplicates)."""
    from apps.documents.models import AuditLog
    from apps.notifications.services import notify_user
    from apps.tasks.models import Task

    from .models import Section
    from .permissions import ensure_project_member

    assignee = assignment.assignee
    if assignee is None:
        return None

    sub_object = assignment.sub_object
    project = sub_object.project
    discipline = assignment.discipline

    # The same section lookup the approval flow uses, so both entry points
    # converge on one Section per project/sub-object/discipline.
    section = Section.objects.filter(
        project=project, sub_object=sub_object, discipline=discipline
    ).first()
    if section is None:
        section = Section.objects.create(
            project=project, sub_object=sub_object, discipline=discipline,
            name=f"{discipline.code} — {sub_object.name}",
        )

    if Task.objects.filter(section=section, assignee=assignee).exists():
        return None

    task = Task.objects.create(
        title=gettext("Develop the project"),
        project=project,
        section=section,
        assignee=assignee,
        creator=actor,
        deadline=assignment.deadline,
    )
    ensure_project_member(project, assignee)
    AuditLog.log(obj=task, action="created", user=actor)
    if assignee.id != actor.id:
        notify_user(
            assignee, "task", _("New task assigned"),
            _('You were assigned to "%(title)s".') % {"title": task.title},
            link=f"/tasks/{task.pk}/",
        )
    return task
