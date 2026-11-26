import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def run_deadline_agent(self):
    """Kunlik AI muddat-nazorati agenti: kechikkan/yaqinlashgan vazifalarni
    tahlil qilib, admin va rahbarlarga hisobot yuboradi."""
    from apps.accounts.models import User
    from apps.notifications.services import notify_user

    from . import services

    if not services.is_configured():
        logger.warning("AI kaliti (GEMINI_API_KEY/ANTHROPIC_API_KEY) o'rnatilmagan — AI muddat agenti o'tkazib yuborildi.")
        return "skipped: no api key"

    try:
        report = services.run_deadline_agent()
    except Exception as exc:
        logger.exception("AI muddat agenti chaqiruvida xato")
        raise self.retry(exc=exc)

    if not report:
        return "skipped: nothing to report"

    recipients = User.objects.filter(
        role__in=[User.Role.ADMIN, User.Role.MANAGER], is_active=True
    )
    for user in recipients:
        notify_user(user, "deadline", "AI: Muddatlar bo'yicha kunlik hisobot", report, link="/tasks/")
    return f"sent to {recipients.count()} recipients"


@shared_task
def remind_office_payments():
    """Zavxoz: takrorlanuvchi ofis to'lovlari (ijara, maosh, kommunal, soliq)
    navbatdagi sanasidan 3 kun oldin va o'sha kuni moliya rollariga eslatma."""
    from .zavxoz import send_payment_reminders

    return send_payment_reminders()
