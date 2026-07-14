from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .models import TelegramLinkToken


@login_required
@require_POST
def link_telegram(request):
    token = TelegramLinkToken.issue(request.user)
    # t.me havolasida @ bo'lmasligi kerak — .env da @ bilan yozilgan bo'lsa olib tashlaymiz
    bot_username = (settings.TELEGRAM_BOT_USERNAME or "your_bot").lstrip("@")
    # Oraliq sahifa avval tg:// (ilovani to'g'ridan-to'g'ri ochadi, t.me
    # bloklangan tarmoqlarda ham ishlaydi), keyin t.me variantini taklif
    # qiladi. Bot /start link_<token> orqali hisobni rolini aniqlagan holda
    # avtomatik ulaydi.
    return render(request, "telegram_bot/link_redirect.html", {
        "app_link": f"tg://resolve?domain={bot_username}&start=link_{token.token}",
        "web_link": f"https://t.me/{bot_username}?start=link_{token.token}",
    })


@login_required
@require_POST
def unlink_telegram(request):
    request.user.telegram_chat_id = None
    request.user.save(update_fields=["telegram_chat_id"])
    messages.success(request, _("Telegram account unlinked."))
    return redirect("accounts:profile")
