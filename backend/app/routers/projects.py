from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User, UserRole
from app.models.project import Project, ProjectMember, SubObject, Section, ProjectStatus
from app.models.task import Task
from app.models.document import AuditLog
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse,
    ProjectMemberCreate, ProjectMemberResponse, SubObjectCreate, SubObjectResponse,
    SectionCreate, SectionResponse,
)
from app.schemas.document import AuditLogResponse
from app.utils.dependencies import get_current_active_user

router = APIRouter(prefix="/projects", tags=["projects"])


async def get_project_or_404(project_id: str, db: AsyncSession) -> Project:
    result = await db.execute(
        select(Project)
        .options(
            selectinload(Project.members),
            selectinload(Project.sub_objects),
            selectinload(Project.sections),
        )
        .where(Project.id == project_id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectListResponse])
async def list_projects(
    status: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(Project)

    if current_user.role not in [UserRole.admin, UserRole.manager]:
        member_subq = select(ProjectMember.project_id).where(
            ProjectMember.user_id == current_user.id,
            or_(ProjectMember.expires_at == None, ProjectMember.expires_at > datetime.utcnow()),
        )
        query = query.where(Project.id.in_(member_subq))

    if status:
        query = query.where(Project.status == status)
    if search:
        query = query.where(Project.name.ilike(f"%{search}%"))

    result = await db.execute(query.order_by(Project.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=ProjectResponse, status_code=201)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = Project(**data.model_dump(), created_by=current_user.id)
    db.add(project)
    await db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=current_user.id, role_in_project="owner"))
    await db.commit()
    return await get_project_or_404(project.id, db)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await get_project_or_404(project_id, db)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    project = await get_project_or_404(project_id, db)

    changes = {}
    for field, value in data.model_dump(exclude_none=True).items():
        old = getattr(project, field, None)
        if old != value:
            changes[field] = {
                "old": old.value if hasattr(old, "value") else str(old),
                "new": value.value if hasattr(value, "value") else str(value),
            }
        setattr(project, field, value)

    if changes:
        db.add(AuditLog(
            entity_type="project", entity_id=project_id,
            action="update", user_id=current_user.id,
            details=changes,
        ))

    await db.commit()
    return await get_project_or_404(project_id, db)


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in [UserRole.admin, UserRole.manager]:
        raise HTTPException(status_code=403, detail="Not allowed")
    project = await get_project_or_404(project_id, db)
    await db.delete(project)
    await db.commit()
    return {"message": "Project deleted"}


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=201)
async def add_member(
    project_id: str,
    data: ProjectMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    existing = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == data.user_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member")

    member = ProjectMember(project_id=project_id, **data.model_dump())
    db.add(member)
    await db.commit()
    await db.refresh(member)
    return member


@router.delete("/{project_id}/members/{user_id}")
async def remove_member(
    project_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    await db.delete(member)
    await db.commit()
    return {"message": "Member removed"}


@router.post("/{project_id}/objects", response_model=SubObjectResponse, status_code=201)
async def add_sub_object(
    project_id: str,
    data: SubObjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    obj = SubObject(project_id=project_id, **data.model_dump())
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


@router.post("/{project_id}/sections", response_model=SectionResponse, status_code=201)
async def add_section(
    project_id: str,
    data: SectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    section = Section(project_id=project_id, **data.model_dump())
    db.add(section)
    await db.commit()
    await db.refresh(section)
    return section


@router.get("/{project_id}/history", response_model=list[AuditLogResponse])
async def get_project_history(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await get_project_or_404(project_id, db)
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.entity_type == "project", AuditLog.entity_id == project_id)
        .order_by(AuditLog.created_at.desc())
        .limit(200)
    )
    return result.scalars().all()


@router.get("/{project_id}/stats")
async def get_project_stats(
    project_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    tasks_result = await db.execute(select(Task).where(Task.project_id == project_id))
    tasks = tasks_result.scalars().all()
    from datetime import datetime
    now = datetime.utcnow()
    from app.models.task import TaskStatus
    return {
        "total_tasks": len(tasks),
        "completed_tasks": sum(1 for t in tasks if t.status == TaskStatus.completed),
        "in_progress_tasks": sum(1 for t in tasks if t.status == TaskStatus.in_progress),
        "overdue_tasks": sum(1 for t in tasks if t.deadline and t.deadline < now and t.status not in [TaskStatus.completed, TaskStatus.approved]),
    }
