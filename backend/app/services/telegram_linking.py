import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)

# Store pending linking requests in memory (in production, use cache/database)
pending_links: dict[str, dict] = {}


def generate_linking_token(user_id: str) -> str:
    """Generate a unique token for linking Telegram to platform account"""
    token = secrets.token_urlsafe(32)
    pending_links[token] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(minutes=30),
    }
    logger.info(f"Generated linking token for user {user_id}")
    return token


def get_link_request(token: str) -> Optional[dict]:
    """Get pending link request"""
    if token not in pending_links:
        return None

    link_data = pending_links[token]
    if link_data["expires_at"] < datetime.utcnow():
        del pending_links[token]
        logger.warning(f"Link token expired: {token}")
        return None

    return link_data


async def link_telegram_account(
    db: AsyncSession,
    token: str,
    telegram_chat_id: str,
    telegram_username: str,
) -> tuple[bool, str]:
    """Link Telegram account to platform user"""
    link_data = get_link_request(token)

    if not link_data:
        return False, "❌ Token expired or invalid"

    try:
        user_id = link_data["user_id"]
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return False, "❌ User not found"

        # Link Telegram account
        user.telegram_chat_id = telegram_chat_id
        await db.commit()

        # Remove used token
        del pending_links[token]

        logger.info(f"Linked Telegram {telegram_username} to user {user.email}")
        return True, f"✅ Telegram account linked successfully!\n\nUser: {user.full_name}\nRole: {user.role}"

    except Exception as e:
        logger.error(f"Error linking Telegram account: {e}")
        return False, "❌ Error linking account"


async def unlink_telegram_account(db: AsyncSession, user_id: str) -> bool:
    """Unlink Telegram account from platform user"""
    try:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            return False

        old_chat_id = user.telegram_chat_id
        user.telegram_chat_id = None
        await db.commit()

        logger.info(f"Unlinked Telegram {old_chat_id} from user {user.email}")
        return True

    except Exception as e:
        logger.error(f"Error unlinking Telegram: {e}")
        return False


async def get_user_by_telegram_id(
    db: AsyncSession,
    telegram_chat_id: str,
) -> Optional[User]:
    """Get platform user by Telegram chat ID"""
    try:
        result = await db.execute(
            select(User).where(User.telegram_chat_id == str(telegram_chat_id))
        )
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Error fetching user by telegram ID: {e}")
        return None


def get_telegram_link_url(user_id: str, token: str) -> str:
    """Generate Telegram bot link for account linking"""
    return f"https://t.me/AiSupport1_bot?start=link_{token}"


def clear_expired_tokens():
    """Clear expired linking tokens"""
    now = datetime.utcnow()
    expired = [token for token, data in pending_links.items() if data["expires_at"] < now]
    for token in expired:
        del pending_links[token]
    if expired:
        logger.info(f"Cleared {len(expired)} expired linking tokens")
