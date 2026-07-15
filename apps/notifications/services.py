from .models import Notification


def notify_user(user, ntype, title, message, link=None):
    """Single choke-point for creating notifications. Creates the DB row
    immediately (drives the bell/badge), then dispatches email/Telegram
    delivery as Celery tasks so slow SMTP/Telegram calls never block the
    request that triggered the notification."""
    prefs = getattr(user, "notification_preference", None)

    notification = None
    if prefs is None or prefs.allows_channel(ntype, "site"):
        notification = Notification.objects.create(
            user=user, type=ntype, title=title, message=message, link=link
        )

    from .tasks import send_notification_email, send_notification_telegram

    if prefs is None or prefs.allows_channel(ntype, "email"):
        send_notification_email.delay(str(user.pk), title, message, link)
    if user.telegram_chat_id and (prefs is None or prefs.allows_channel(ntype, "telegram")):
        send_notification_telegram.delay(str(user.pk), title, message)

    return notification
