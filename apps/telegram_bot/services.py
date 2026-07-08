import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def _bot():
    if not settings.TELEGRAM_BOT_TOKEN:
        return None
    from telegram import Bot
    return Bot(token=settings.TELEGRAM_BOT_TOKEN)


def send_message(chat_id, text, parse_mode="HTML"):
    """Fire-and-forget outbound message. No-ops quietly if the bot token
    isn't configured (e.g. local dev without a Telegram bot set up)."""
    bot = _bot()
    if bot is None:
        logger.debug("Telegram bot not configured; skipping message to %s", chat_id)
        return
    import asyncio
    try:
        asyncio.run(bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode))
    except Exception:
        logger.exception("Failed to send Telegram message to %s", chat_id)
