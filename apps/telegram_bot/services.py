import logging

from apps.core.runtime_config import get_config

logger = logging.getLogger(__name__)


def _bot():
    token = get_config("TELEGRAM_BOT_TOKEN")
    if not token:
        return None
    from telegram import Bot
    return Bot(token=token)


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


def send_document(chat_id, fileobj, filename, caption=""):
    """Faylni chatga yuboradi. True — yuborildi; bot sozlanmagan yoki
    Telegram rad etsa False (sabab logga yoziladi)."""
    bot = _bot()
    if bot is None:
        logger.debug("Telegram bot not configured; skipping document to %s", chat_id)
        return False
    import asyncio

    from telegram import InputFile
    try:
        asyncio.run(bot.send_document(
            chat_id=chat_id, document=InputFile(fileobj, filename=filename),
            caption=caption[:1024], read_timeout=120, write_timeout=120,
        ))
    except Exception:
        logger.exception("Failed to send Telegram document to %s", chat_id)
        return False
    return True
