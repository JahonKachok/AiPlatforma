def resolve_project_gip(project):
    """The GIP attached to the project itself — the person who signs work off.
    Ordered by join date so a project with several GIPs always resolves to the
    same one rather than whichever the database happens to return first."""
    member = (
        project.members.filter(role_in_project="gip")
        .select_related("user").order_by("joined_at").first()
    )
    return member.user if member else None


def resolve_gip_reviewer(sub_object, project):
    """Walk up from the sub-object (a pod object's own GIP takes priority over
    its parent object's) to find who should review work submitted on it; falls
    back to the project's GIP member if neither the object nor its parent has one."""
    candidate = sub_object
    while candidate is not None:
        if candidate.gip_id:
            return candidate.gip
        candidate = candidate.parent
    return resolve_project_gip(project)
