import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.telegram_bot import telegram_bot
from app.services.telegram_service import telegram_service
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/telegram", tags=["telegram"])


class TelegramWebhookData(BaseModel):
    update_id: int
    message: dict = None
    callback_query: dict = None
    web_app_data: dict = None


class SendMessageRequest(BaseModel):
    message: str
    parse_mode: str = "HTML"


class SendNotificationRequest(BaseModel):
    title: str
    description: str
    notification_type: str = "info"  # info, warning, error, success


@router.post("/webhook")
async def telegram_webhook(data: dict):
    """Handle Telegram webhook updates"""
    try:
        success = await telegram_bot.process_update(data)
        if success:
            return {"ok": True}
        return {"ok": False}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


@router.post("/send-message")
async def send_telegram_message(
    request: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send message to user"""
    if not settings.TELEGRAM_USER_ID:
        raise HTTPException(status_code=400, detail="Telegram user ID not configured")

    success = await telegram_service.send_message(
        chat_id=settings.TELEGRAM_USER_ID,
        text=request.message,
        parse_mode=request.parse_mode,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send message")

    return {"ok": True, "message": "Message sent successfully"}


@router.post("/send-notification")
async def send_notification(
    request: SendNotificationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Send notification to user"""
    if not settings.TELEGRAM_USER_ID:
        raise HTTPException(status_code=400, detail="Telegram user ID not configured")

    emoji_map = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "success": "✅",
    }
    emoji = emoji_map.get(request.notification_type, "📢")

    text = f"{emoji} <b>{request.title}</b>\n\n{request.description}"

    success = await telegram_service.send_message(
        chat_id=settings.TELEGRAM_USER_ID,
        text=text,
        parse_mode="HTML",
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send notification")

    return {"ok": True, "message": "Notification sent successfully"}


@router.get("/info")
async def get_bot_info():
    """Get bot information"""
    if not telegram_service.enabled:
        raise HTTPException(status_code=400, detail="Telegram bot not configured")

    try:
        bot_info = await telegram_service.bot.get_me()
        return {
            "username": bot_info.username,
            "name": bot_info.first_name,
            "user_id": settings.TELEGRAM_USER_ID,
        }
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get bot info")


@router.post("/set-webhook")
async def set_webhook(webhook_url: str):
    """Set webhook URL"""
    if not telegram_bot.app:
        raise HTTPException(status_code=400, detail="Telegram bot not initialized")

    try:
        await telegram_bot.app.bot.set_webhook(url=webhook_url)
        return {"ok": True, "message": "Webhook set successfully"}
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to set webhook")


@router.delete("/remove-webhook")
async def remove_webhook():
    """Remove webhook"""
    if not telegram_bot.app:
        raise HTTPException(status_code=400, detail="Telegram bot not initialized")

    try:
        await telegram_bot.app.bot.delete_webhook()
        return {"ok": True, "message": "Webhook removed"}
    except Exception as e:
        logger.error(f"Failed to remove webhook: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove webhook")
