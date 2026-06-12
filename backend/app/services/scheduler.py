"""Background deadline watcher: reminds about upcoming deadlines and flags overdue items."""
import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.task import Task, TaskStatus
from app.models.document import Document, DocumentStatus
from app.models.project import Project, ProjectStatus
from app.models.notification import Notification, NotificationType
from app.services.notify import notify_user

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 3600  # hourly
REMINDER_WINDOW_HOURS = 24
DEDUP_WINDOW_HOURS = 23

ACTIVE_TASK_STATUSES = [TaskStatus.new, TaskStatus.in_progress, TaskStatus.review, TaskStatus.revision]


async def _already_notified(db, user_id: str, link: str, since: datetime) -> bool:
    result = await db.execute(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.link == link,
            Notification.type == NotificationType.deadline,
            Notification.created_at >= since,
        ).limit(1)
    )
    return result.scalar_one_or_none() is not None


async def check_deadlines_once():
    now = datetime.utcnow()
    window_end = now + timedelta(hours=REMINDER_WINDOW_HOURS)
    dedup_since = now - timedelta(hours=DEDUP_WINDOW_HOURS)

    async with AsyncSessionLocal() as db:
        # Tasks: upcoming deadlines
        result = await db.execute(
            select(Task).where(
                Task.deadline != None,
                Task.deadline >= now,
                Task.deadline <= window_end,
                Task.status.in_(ACTIVE_TASK_STATUSES),
                Task.assignee_id != None,
            )
        )
        for task in result.scalars().all():
            link = f"/tasks?id={task.id}"
            if await _already_notified(db, task.assignee_id, link, dedup_since):
                continue
            await notify_user(
                db, task.assignee_id, NotificationType.deadline,
                "Muddat yaqinlashmoqda",
                f"'{task.title}' vazifasining muddati: {task.deadline.strftime('%d.%m.%Y %H:%M')}",
                link,
            )

        # Tasks: overdue
        result = await db.execute(
            select(Task).where(
                Task.deadline != None,
                Task.deadline < now,
                Task.status.in_(ACTIVE_TASK_STATUSES),
            )
        )
        for task in result.scalars().all():
            link = f"/tasks?id={task.id}&overdue=1"
            for uid in {task.assignee_id, task.creator_id}:
                if not uid:
                    continue
                if await _already_notified(db, uid, link, dedup_since):
                    continue
                await notify_user(
                    db, uid, NotificationType.deadline,
                    "Muddat o'tib ketdi",
                    f"'{task.title}' vazifasining muddati o'tib ketdi ({task.deadline.strftime('%d.%m.%Y')})",
                    link,
                )

        # Documents with approaching deadline
        result = await db.execute(
            select(Document).where(
                Document.deadline != None,
                Document.deadline >= now,
                Document.deadline <= window_end,
                Document.status.notin_([DocumentStatus.approved, DocumentStatus.archived]),
            )
        )
        for doc in result.scalars().all():
            link = f"/documents?id={doc.id}"
            if await _already_notified(db, doc.uploaded_by, link, dedup_since):
                continue
            await notify_user(
                db, doc.uploaded_by, NotificationType.deadline,
                "Hujjat muddati yaqinlashmoqda",
                f"'{doc.name}' hujjatining muddati: {doc.deadline.strftime('%d.%m.%Y')}",
                link,
            )

        # Projects with approaching deadline -> notify creator
        result = await db.execute(
            select(Project).where(
                Project.deadline != None,
                Project.deadline >= now,
                Project.deadline <= window_end,
                Project.status == ProjectStatus.active,
            )
        )
        for proj in result.scalars().all():
            link = f"/projects/{proj.id}"
            if await _already_notified(db, proj.created_by, link, dedup_since):
                continue
            await notify_user(
                db, proj.created_by, NotificationType.deadline,
                "Loyiha muddati yaqinlashmoqda",
                f"'{proj.name}' loyihasining muddati: {proj.deadline.strftime('%d.%m.%Y')}",
                link,
            )

        await db.commit()


async def deadline_watcher():
    while True:
        try:
            await check_deadlines_once()
            logger.info("Deadline check completed")
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Deadline check failed: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
