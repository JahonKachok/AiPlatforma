from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST

from .models import TelegramLinkToken


@login_required
@require_POST
def link_telegram(request):
    token = TelegramLinkToken.issue(request.user)
    bot_username = settings.TELEGRAM_BOT_USERNAME or "your_bot"
    deep_link = f"https://t.me/{bot_username}?start=link_{token.token}"
    messages.success(
        request,
        _('Open Telegram and start a chat with the bot to link your account: %(link)s') % {"link": deep_link},
    )
    return redirect("accounts:profile")


@login_required
@require_POST
def unlink_telegram(request):
    request.user.telegram_chat_id = None
    request.user.save(update_fields=["telegram_chat_id"])
    messages.success(request, _("Telegram account unlinked."))
    return redirect("accounts:profile")
