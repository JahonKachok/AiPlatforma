import io
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from app.database import get_db
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus
from app.models.document import Document, ApprovalStage, ApprovalStatus
from app.models.finance import FinancialRecord, EmployeeContract, RecordType, RecordStatus
from app.models.notification import Notification
from app.utils.dependencies import get_current_active_user

router = APIRouter(prefix="/reports", tags=["reports"])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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

    pending_approvals_result = await db.execute(
        select(func.count()).where(ApprovalStage.status == ApprovalStatus.pending)
    )
    pending_approvals = pending_approvals_result.scalar() or 0

    finance_result = await db.execute(select(FinancialRecord))
    records = finance_result.scalars().all()

    active_statuses = [TaskStatus.new, TaskStatus.in_progress, TaskStatus.review, TaskStatus.revision]
    user_names = {u.id: u.full_name for u in users}
    workload: dict[str, int] = {}
    for t in tasks:
        if t.assignee_id and t.status in active_statuses:
            workload[t.assignee_id] = workload.get(t.assignee_id, 0) + 1
    workload_list = sorted(
        (
            {"user_id": uid, "name": user_names.get(uid, "—"), "active_tasks": count}
            for uid, count in workload.items()
        ),
        key=lambda w: -w["active_tasks"],
    )

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
        "approvals": {
            "pending": pending_approvals,
        },
        "finance": {
            "total_income": sum(r.amount for r in records if r.type == RecordType.income and r.status == RecordStatus.confirmed),
            "total_expense": sum(r.amount for r in records if r.type == RecordType.expense and r.status == RecordStatus.confirmed),
        },
        "workload": workload_list[:10],
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


@router.get("/employees")
async def get_employees_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    users_result = await db.execute(select(User).where(User.is_active == True))
    users = users_result.scalars().all()
    tasks_result = await db.execute(select(Task))
    tasks = tasks_result.scalars().all()
    contracts_result = await db.execute(select(EmployeeContract))
    contracts = contracts_result.scalars().all()

    now = datetime.utcnow()
    report = []
    for u in users:
        user_tasks = [t for t in tasks if t.assignee_id == u.id]
        completed = [t for t in user_tasks if t.status == TaskStatus.completed]
        user_contracts = [c for c in contracts if c.user_id == u.id]
        report.append({
            "user_id": u.id,
            "name": u.full_name,
            "role": u.role.value,
            "total_tasks": len(user_tasks),
            "completed_tasks": len(completed),
            "in_progress_tasks": sum(1 for t in user_tasks if t.status == TaskStatus.in_progress),
            "overdue_tasks": sum(
                1 for t in user_tasks
                if t.deadline and t.deadline < now and t.status not in [TaskStatus.completed, TaskStatus.approved]
            ),
            "contract_amount": sum(c.amount for c in user_contracts),
            "paid": sum(c.paid for c in user_contracts),
            "balance": sum(c.amount - c.paid for c in user_contracts),
        })
    return report


def _make_workbook(title: str, headers: list[str], rows: list[list]):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(row)
    for idx, col in enumerate(ws.columns, start=1):
        width = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(width + 2, 60)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


@router.get("/export/{kind}")
async def export_report(
    kind: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    now = datetime.utcnow()

    if kind == "projects":
        result = await db.execute(select(Project))
        projects = result.scalars().all()
        headers = ["Nomi", "Buyurtmachi", "Manzil", "Bosqich", "Holat", "Muddat", "Budjet", "To'langan"]
        rows = [
            [p.name, p.client_name, p.address, p.stage.value, p.status.value,
             p.deadline.strftime("%d.%m.%Y") if p.deadline else "", p.budget, p.paid_amount]
            for p in projects
        ]
        buf = _make_workbook("Loyihalar", headers, rows)
    elif kind == "tasks":
        result = await db.execute(select(Task))
        tasks = result.scalars().all()
        users_result = await db.execute(select(User))
        user_names = {u.id: u.full_name for u in users_result.scalars().all()}
        headers = ["Vazifa", "Holat", "Muhimlik", "Ijrochi", "Muddat", "Muddati o'tgan"]
        rows = [
            [t.title, t.status.value, t.priority.value, user_names.get(t.assignee_id, ""),
             t.deadline.strftime("%d.%m.%Y") if t.deadline else "",
             "Ha" if t.deadline and t.deadline < now and t.status not in [TaskStatus.completed, TaskStatus.approved] else "Yo'q"]
            for t in tasks
        ]
        buf = _make_workbook("Vazifalar", headers, rows)
    elif kind == "finance":
        result = await db.execute(select(FinancialRecord))
        records = result.scalars().all()
        headers = ["Sana", "Turi", "Summa", "Valyuta", "Kategoriya", "Holat", "Izoh"]
        rows = [
            [r.date.strftime("%d.%m.%Y"), r.type.value, r.amount, r.currency,
             r.category or "", r.status.value, r.description or ""]
            for r in records
        ]
        buf = _make_workbook("Moliya", headers, rows)
    elif kind == "employees":
        report = await get_employees_report(db=db, current_user=current_user)
        headers = ["Xodim", "Rol", "Vazifalar", "Bajarilgan", "Jarayonda", "Muddati o'tgan", "Shartnoma", "To'langan", "Qoldiq"]
        rows = [
            [r["name"], r["role"], r["total_tasks"], r["completed_tasks"], r["in_progress_tasks"],
             r["overdue_tasks"], r["contract_amount"], r["paid"], r["balance"]]
            for r in report
        ]
        buf = _make_workbook("Xodimlar", headers, rows)
    else:
        raise HTTPException(status_code=400, detail="Unknown export kind. Use: projects, tasks, finance, employees")

    filename = f"{kind}_report_{now.strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buf, media_type=XLSX_MIME,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
