import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self):
        self.bot = None
        self.enabled = False

    async def initialize(self):
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.info("Telegram bot token not configured, skipping initialization")
            return

        try:
            from telegram import Bot
            self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            bot_info = await self.bot.get_me()
            logger.info(f"Telegram bot initialized: @{bot_info.username}")
            self.enabled = True
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")

    async def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        if not self.enabled or not self.bot:
            return False
        try:
            await self.bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message to {chat_id}: {e}")
            return False

    async def send_task_notification(self, chat_id: str, task_title: str, task_id: str, action: str) -> bool:
        text = (
            f"📋 <b>Vazifa {action}</b>\n\n"
            f"<b>{task_title}</b>\n\n"
            f"Platformada ko'rish uchun: /task_{task_id}"
        )
        return await self.send_message(chat_id, text)

    async def send_approval_notification(self, chat_id: str, document_name: str, document_id: str, status: str) -> bool:
        emoji = "✅" if status == "approved" else "❌"
        text = (
            f"{emoji} <b>Hujjat {status}</b>\n\n"
            f"<b>{document_name}</b>\n\n"
            f"Platformada ko'rish uchun: /doc_{document_id}"
        )
        return await self.send_message(chat_id, text)

    async def send_deadline_reminder(self, chat_id: str, title: str, deadline: str) -> bool:
        text = (
            f"⚠️ <b>Muddat yaqinlashmoqda</b>\n\n"
            f"<b>{title}</b>\n"
            f"Muddat: {deadline}"
        )
        return await self.send_message(chat_id, text)

    async def send_file(self, chat_id: str, file_path: str, caption: Optional[str] = None) -> bool:
        if not self.enabled or not self.bot:
            return False
        try:
            with open(file_path, "rb") as f:
                await self.bot.send_document(chat_id=chat_id, document=f, caption=caption)
            return True
        except Exception as e:
            logger.error(f"Failed to send file to {chat_id}: {e}")
            return False


telegram_service = TelegramService()
