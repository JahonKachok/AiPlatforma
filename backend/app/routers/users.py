from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User, UserRole
from app.models.task import Task, TaskStatus
from app.models.project import ProjectMember
from app.schemas.user import UserResponse, UserUpdate, UserStatsResponse
from app.utils.dependencies import get_current_active_user, require_roles
from app.services.file_service import save_upload_file, get_file_url

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(User).where(User.is_active == True))
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.id != user_id and current_user.role not in [UserRole.admin, UserRole.manager]:
        raise HTTPException(status_code=403, detail="Not allowed")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    for field, value in data.model_dump(exclude_none=True).items():
        if field == "role" and current_user.role != UserRole.admin:
            continue
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.admin)),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    await db.commit()
    return {"message": "User deactivated"}


@router.post("/{user_id}/avatar", response_model=UserResponse)
async def upload_avatar(
    user_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.id != user_id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Not allowed")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    file_path, _ = await save_upload_file(file, f"avatars/{user_id}")
    user.avatar_url = get_file_url(file_path)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}/stats", response_model=UserStatsResponse)
async def get_user_stats(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    tasks_result = await db.execute(select(Task).where(Task.assignee_id == user_id))
    tasks = tasks_result.scalars().all()

    from datetime import datetime
    now = datetime.utcnow()

    projects_result = await db.execute(
        select(func.count()).where(ProjectMember.user_id == user_id)
    )
    active_projects = projects_result.scalar() or 0

    return UserStatsResponse(
        tasks_total=len(tasks),
        tasks_completed=sum(1 for t in tasks if t.status == TaskStatus.completed),
        tasks_in_progress=sum(1 for t in tasks if t.status == TaskStatus.in_progress),
        tasks_overdue=sum(1 for t in tasks if t.deadline and t.deadline < now and t.status not in [TaskStatus.completed, TaskStatus.approved]),
        active_projects=active_projects,
    )
