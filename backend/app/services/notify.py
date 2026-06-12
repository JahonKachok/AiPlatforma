"""Unified notification dispatch: DB record + WebSocket push + Telegram + Email."""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.models.user import User
from app.websocket.manager import manager
from app.services.telegram_service import telegram_service
from app.services.email_service import email_service

logger = logging.getLogger(__name__)


async def notify_user(
    db: AsyncSession,
    user_id: str,
    type: NotificationType,
    title: str,
    message: str,
    link: str | None = None,
    send_email: bool = True,
    send_telegram: bool = True,
) -> Notification:
    """Create a DB notification and push it through all configured channels.

    Caller is responsible for committing the session.
    """
    notification = Notification(
        user_id=user_id, type=type, title=title, message=message, link=link,
    )
    db.add(notification)

    try:
        await manager.send_to_user(user_id, {
            "type": "notification",
            "notification_type": type.value,
            "title": title,
            "message": message,
            "link": link,
        })
    except Exception as e:
        logger.warning(f"WS push failed for {user_id}: {e}")

    if send_email or send_telegram:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            if send_telegram and user.telegram_chat_id:
                try:
                    await telegram_service.send_message(
                        user.telegram_chat_id, f"<b>{title}</b>\n\n{message}"
                    )
                except Exception as e:
                    logger.warning(f"Telegram send failed for {user_id}: {e}")
            if send_email and user.email:
                try:
                    await email_service.send_notification_email(user.email, title, message, link)
                except Exception as e:
                    logger.warning(f"Email send failed for {user_id}: {e}")

    return notification
