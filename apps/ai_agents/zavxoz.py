"""Zavxoz: ofis to'lovlari kalendari va eslatmalari (LLM'siz)."""
from datetime import timedelta

from django.utils import timezone

from apps.accounts.models import User
from apps.finance.models import AdministrativeExpense
from apps.notifications.models import Notification
from apps.notifications.services import notify_user

# AdministrativeExpense.category -> o'qiladigan nom
RECURRING = {"rent": "Аренда", "utilities": "Коммунальные", "tax": "Налоги", "Зарплата": "Зарплата"}
PERIOD_DAYS = {"month": 30, "quarter": 91, "year": 365}
REMIND_BEFORE = (3, 0)
TITLE = "Завхоз: оплата «{name}»"


def _add_period(day, period):
    if period == "month":
        month = day.month % 12 + 1
        year = day.year + (day.month == 12)
        for d in (day.day, 30, 29, 28):
            try:
                return day.replace(year=year, month=month, day=d)
            except ValueError:
                continue
    return day + timedelta(days=PERIOD_DAYS.get(period, 30))


def upcoming(today=None):
    """[(toifa nomi, keyingi sana, oxirgi summa, valyuta)] — har toifaning oxirgi
    to'lovidan bir davr keyin."""
    today = today or timezone.localdate()
    out = []
    for category, name in RECURRING.items():
        last = AdministrativeExpense.objects.filter(category=category, period__in=PERIOD_DAYS).order_by("-date").first()
        if last is None:
            continue
        due = _add_period(last.date, last.period)
        out.append((name, due, last.amount, last.currency))
    return sorted(out, key=lambda r: r[1])


def send_payment_reminders(today=None):
    today = today or timezone.localdate()
    since = timezone.now() - timedelta(hours=20)
    users = User.objects.filter(is_active=True, role__in=(User.Role.ADMIN, User.Role.MANAGER, User.Role.FINANCE))
    sent = 0
    for name, due, amount, currency in upcoming(today):
        days = (due - today).days
        if days not in REMIND_BEFORE and not (days < 0 and days >= -7):
            continue
        title = TITLE.format(name=name)
        money = f"{amount:,.0f}".replace(",", " ") + (" USD" if currency == "USD" else " сум")
        when = "сегодня" if days == 0 else (f"через {days} дн." if days > 0 else f"просрочено на {-days} дн.")
        for user in users:
            if Notification.objects.filter(user=user, title=title, created_at__gte=since).exists():
                continue
            notify_user(user, "finance", title, f"{name}: {when} ({due:%d.%m.%Y}), прошлый платёж {money}.",
                        link="/finance/?tab=admin_expenses")
            sent += 1
    return sent
