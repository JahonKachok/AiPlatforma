from .models import Notification


def notify_user(user, ntype, title, message, link=None, telegram_buttons=None, send_telegram=True):
    """Single choke-point for creating notifications. Creates the DB row
    immediately (drives the bell/badge), then dispatches email/Telegram
    delivery as Celery tasks so slow SMTP/Telegram calls never block the
    request that triggered the notification.

    telegram_buttons — Telegram xabari ostidagi inline tugmalar:
    [[(matn, callback_data), ...], ...] (Pult dispetcheri: «Принять», foizlar).
    send_telegram=False — Telegram'ga chaqiruvchining o'zi alohida yuboradi."""
    prefs = getattr(user, "notification_preference", None)

    notification = None
    if prefs is None or prefs.allows_channel(ntype, "site"):
        notification = Notification.objects.create(
            user=user, type=ntype, title=title, message=message, link=link
        )

    from .tasks import send_notification_email, send_notification_telegram

    if prefs is None or prefs.allows_channel(ntype, "email"):
        send_notification_email.delay(str(user.pk), title, message, link)
    if send_telegram and user.telegram_chat_id and (prefs is None or prefs.allows_channel(ntype, "telegram")):
        send_notification_telegram.delay(str(user.pk), title, message, telegram_buttons)

    return notification
