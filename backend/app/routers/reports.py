from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus
from app.models.document import Document
from app.models.finance import FinancialRecord, RecordType, RecordStatus
from app.models.notification import Notification
from app.utils.dependencies import get_current_active_user

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    projects_result = await db.execute(select(Project))
    projects = projects_result.scalars().all()

    tasks_result = await db.execute(select(Task))
    tasks = tasks_result.scalars().all()

    users_result = await db.execute(select(User).where(User.is_active == True))
    users = users_result.scalars().all()

    docs_result = await db.execute(select(Document))
    docs = docs_result.scalars().all()

    now = datetime.utcnow()
    overdue_tasks = [t for t in tasks if t.deadline and t.deadline < now and t.status not in [TaskStatus.completed, TaskStatus.approved]]

    recent_deadline = now + timedelta(days=7)
    upcoming_deadlines = [
        {"id": t.id, "title": t.title, "deadline": t.deadline.isoformat(), "type": "task"}
        for t in tasks
        if t.deadline and now <= t.deadline <= recent_deadline and t.status not in [TaskStatus.completed, TaskStatus.approved]
    ]
    upcoming_deadlines += [
        {"id": p.id, "title": p.name, "deadline": p.deadline.isoformat(), "type": "project"}
        for p in projects
        if p.deadline and now <= p.deadline <= recent_deadline and p.status == ProjectStatus.active
    ]

    return {
        "projects": {
            "total": len(projects),
            "active": sum(1 for p in projects if p.status == ProjectStatus.active),
            "completed": sum(1 for p in projects if p.status == ProjectStatus.completed),
        },
        "tasks": {
            "total": len(tasks),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.completed),
            "in_progress": sum(1 for t in tasks if t.status == TaskStatus.in_progress),
            "overdue": len(overdue_tasks),
        },
        "users": {
            "total": len(users),
            "active": sum(1 for u in users if u.is_active),
        },
        "documents": {
            "total": len(docs),
        },
        "upcoming_deadlines": upcoming_deadlines[:10],
    }


@router.get("/projects")
async def get_projects_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Project))
    projects = result.scalars().all()

    by_stage = {}
    by_status = {}
    for p in projects:
        by_stage[p.stage.value] = by_stage.get(p.stage.value, 0) + 1
        by_status[p.status.value] = by_status.get(p.status.value, 0) + 1

    return {
        "total": len(projects),
        "by_stage": by_stage,
        "by_status": by_status,
        "total_budget": sum(p.budget for p in projects),
        "total_paid": sum(p.paid_amount for p in projects),
    }


@router.get("/tasks")
async def get_tasks_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(Task))
    tasks = result.scalars().all()

    by_status = {}
    by_priority = {}
    for t in tasks:
        by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
        by_priority[t.priority.value] = by_priority.get(t.priority.value, 0) + 1

    now = datetime.utcnow()
    overdue = [t for t in tasks if t.deadline and t.deadline < now and t.status not in [TaskStatus.completed, TaskStatus.approved]]

    return {
        "total": len(tasks),
        "by_status": by_status,
        "by_priority": by_priority,
        "overdue": len(overdue),
    }


@router.get("/finance")
async def get_finance_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(select(FinancialRecord))
    records = result.scalars().all()

    monthly = {}
    for r in records:
        month_key = r.date.strftime("%Y-%m")
        if month_key not in monthly:
            monthly[month_key] = {"income": 0, "expense": 0}
        if r.type == RecordType.income:
            monthly[month_key]["income"] += r.amount
        elif r.type == RecordType.expense:
            monthly[month_key]["expense"] += r.amount

    return {
        "total_income": sum(r.amount for r in records if r.type == RecordType.income and r.status == RecordStatus.confirmed),
        "total_expense": sum(r.amount for r in records if r.type == RecordType.expense and r.status == RecordStatus.confirmed),
        "monthly": monthly,
    }


@router.get("/users/{user_id}/performance")
async def get_user_performance(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    tasks_result = await db.execute(select(Task).where(Task.assignee_id == user_id))
    tasks = tasks_result.scalars().all()
    now = datetime.utcnow()

    completed = [t for t in tasks if t.status == TaskStatus.completed]
    on_time = [t for t in completed if not t.deadline or t.updated_at <= t.deadline]

    return {
        "user_id": user_id,
        "total_tasks": len(tasks),
        "completed_tasks": len(completed),
        "completion_rate": round(len(completed) / len(tasks) * 100, 1) if tasks else 0,
        "on_time_rate": round(len(on_time) / len(completed) * 100, 1) if completed else 0,
        "overdue_tasks": sum(1 for t in tasks if t.deadline and t.deadline < now and t.status not in [TaskStatus.completed, TaskStatus.approved]),
    }
