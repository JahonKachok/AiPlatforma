from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.task import Task, TaskComment, TaskAttachment, TaskStatus
from app.models.notification import Notification, NotificationType
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse,
    TaskCommentCreate, TaskCommentUpdate, TaskCommentResponse,
    TaskAttachmentResponse,
)
from app.utils.dependencies import get_current_active_user
from app.services.file_service import save_upload_file, get_file_url, delete_file
from app.websocket.manager import manager

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def get_task_or_404(task_id: str, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task)
        .options(selectinload(Task.comments), selectinload(Task.attachments))
        .where(Task.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("", response_model=list[TaskResponse])
async def list_tasks(
    project_id: str | None = None,
    assignee_id: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    query = select(Task).options(selectinload(Task.comments), selectinload(Task.attachments))

    if project_id:
        query = query.where(Task.project_id == project_id)
    if assignee_id:
        query = query.where(Task.assignee_id == assignee_id)
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    if search:
        query = query.where(Task.title.ilike(f"%{search}%"))

    result = await db.execute(query.order_by(Task.created_at.desc()))
    return result.scalars().all()


@router.get("/overdue", response_model=list[TaskResponse])
async def get_overdue_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    now = datetime.utcnow()
    query = (
        select(Task)
        .options(selectinload(Task.comments), selectinload(Task.attachments))
        .where(
            Task.deadline < now,
            Task.status.notin_([TaskStatus.completed, TaskStatus.approved]),
        )
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/calendar", response_model=list[TaskResponse])
async def get_calendar_tasks(
    start: str,
    end: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format")

    query = (
        select(Task)
        .options(selectinload(Task.comments), selectinload(Task.attachments))
        .where(Task.deadline >= start_dt, Task.deadline <= end_dt)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = Task(**data.model_dump(), creator_id=current_user.id)
    db.add(task)
    await db.flush()

    if task.assignee_id and task.assignee_id != current_user.id:
        notification = Notification(
            user_id=task.assignee_id,
            type=NotificationType.task,
            title="Yangi vazifa tayinlandi",
            message=f"Sizga yangi vazifa tayinlandi: {task.title}",
            link=f"/tasks?id={task.id}",
        )
        db.add(notification)
        await manager.send_to_user(task.assignee_id, {
            "type": "notification",
            "title": "Yangi vazifa tayinlandi",
            "message": task.title,
        })

    await db.commit()
    return await get_task_or_404(task.id, db)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return await get_task_or_404(task_id, db)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = await get_task_or_404(task_id, db)
    old_status = task.status

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(task, field, value)

    if data.status and data.status != old_status and task.assignee_id:
        notification = Notification(
            user_id=task.assignee_id,
            type=NotificationType.task,
            title="Vazifa holati o'zgardi",
            message=f"'{task.title}' vazifasi holati: {data.status.value}",
            link=f"/tasks?id={task.id}",
        )
        db.add(notification)

    await db.commit()
    return await get_task_or_404(task_id, db)


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = await get_task_or_404(task_id, db)
    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted"}


@router.post("/{task_id}/comments", response_model=TaskCommentResponse, status_code=201)
async def add_comment(
    task_id: str,
    data: TaskCommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    task = await get_task_or_404(task_id, db)
    comment = TaskComment(task_id=task_id, user_id=current_user.id, content=data.content)
    db.add(comment)

    if task.assignee_id and task.assignee_id != current_user.id:
        notification = Notification(
            user_id=task.assignee_id,
            type=NotificationType.comment,
            title="Yangi izoh",
            message=f"'{task.title}' vazifasiga yangi izoh qo'shildi",
            link=f"/tasks?id={task_id}",
        )
        db.add(notification)

    await db.commit()
    await db.refresh(comment)
    return comment


@router.put("/{task_id}/comments/{comment_id}", response_model=TaskCommentResponse)
async def update_comment(
    task_id: str,
    comment_id: str,
    data: TaskCommentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(TaskComment).where(TaskComment.id == comment_id, TaskComment.task_id == task_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    comment.content = data.content
    await db.commit()
    await db.refresh(comment)
    return comment


@router.delete("/{task_id}/comments/{comment_id}")
async def delete_comment(
    task_id: str,
    comment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(TaskComment).where(TaskComment.id == comment_id, TaskComment.task_id == task_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    await db.delete(comment)
    await db.commit()
    return {"message": "Comment deleted"}


@router.post("/{task_id}/attachments", response_model=TaskAttachmentResponse, status_code=201)
async def upload_attachment(
    task_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    await get_task_or_404(task_id, db)
    file_path, file_size = await save_upload_file(file, f"tasks/{task_id}")
    attachment = TaskAttachment(
        task_id=task_id,
        user_id=current_user.id,
        filename=file.filename or "file",
        file_path=file_path,
        file_size=file_size,
        mime_type=file.content_type,
    )
    db.add(attachment)
    await db.commit()
    await db.refresh(attachment)
    return attachment


@router.delete("/{task_id}/attachments/{attachment_id}")
async def delete_attachment(
    task_id: str,
    attachment_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(TaskAttachment).where(
            TaskAttachment.id == attachment_id,
            TaskAttachment.task_id == task_id,
        )
    )
    attachment = result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    delete_file(attachment.file_path)
    await db.delete(attachment)
    await db.commit()
    return {"message": "Attachment deleted"}
