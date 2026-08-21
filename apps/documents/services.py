def resolve_gip_reviewer(sub_object, project):
    """Walk up from the sub-object (a pod object's own GIP takes priority over
    its parent object's) to find who should review work submitted on it; falls
    back to the project's GIP member if neither the object nor its parent has one."""
    candidate = sub_object
    while candidate is not None:
        if candidate.gip_id:
            return candidate.gip
        candidate = candidate.parent
    member = project.members.filter(role_in_project="gip").select_related("user").first()
    return member.user if member else None
