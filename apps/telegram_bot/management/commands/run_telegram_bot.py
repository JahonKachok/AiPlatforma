from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Runs the Telegram bot in long-polling mode (separate long-running process)."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN is not configured."))
            return

        from telegram import Update
        from telegram.ext import (
            Application,
            CommandHandler,
            ContextTypes,
            MessageHandler,
            TypeHandler,
            filters,
        )

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            args = context.args
            if args and args[0].startswith("link_"):
                await link(update, context, token=args[0][len("link_"):])
                return
            await update.message.reply_html(
                "\U0001F44B Salom! AiPlatforma botiga xush kelibsiz.\n"
                "/link &lt;token&gt; — hisobingizni ulash\n"
                "/whoami — profil ma'lumotlari\n"
                "/help — yordam"
            )

        async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_html(
                "/start — botni ishga tushirish\n"
                "/link &lt;token&gt; — hisobni ulash\n"
                "/unlink — hisobni uzish\n"
                "/whoami — profil ma'lumotlari\n"
                "/miniapp — veb-ilova havolasi"
            )

        @sync_to_async
        def _get_user_by_chat_id(chat_id):
            from apps.accounts.models import User
            return User.objects.filter(telegram_chat_id=str(chat_id)).first()

        async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = await _get_user_by_chat_id(update.effective_chat.id)
            if user:
                await update.message.reply_html(
                    f"<b>{user.full_name}</b>\n{user.email}\n{user.get_role_display()}"
                )
            else:
                await update.message.reply_text("Hisobingiz hali ulanmagan. /link <token> dan foydalaning.")

        async def miniapp(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await update.message.reply_text(f"{settings.FRONTEND_URL}/telegram/miniapp/")

        @sync_to_async
        def _do_link(token, chat_id):
            from apps.telegram_bot.models import TelegramLinkToken

            link_token = TelegramLinkToken.objects.filter(token=token).first()
            if not link_token or not link_token.is_valid():
                return None
            user = link_token.user
            user.telegram_chat_id = str(chat_id)
            user.save(update_fields=["telegram_chat_id"])
            link_token.used_at = timezone.now()
            link_token.save(update_fields=["used_at"])
            return user

        async def link(update: Update, context: ContextTypes.DEFAULT_TYPE, token=None):
            token = token or (context.args[0] if context.args else None)
            if not token:
                await update.message.reply_text("Foydalanish: /link <token>")
                return
            user = await _do_link(token, update.effective_chat.id)
            if user:
                await update.message.reply_html(
                    "✅ Hisobingiz muvaffaqiyatli ulandi!\n\n"
                    f"👤 <b>{user.full_name}</b>\n"
                    f"🎖 Rol: <b>{user.get_role_display()}</b>\n"
                    f"📧 {user.email}\n\n"
                    "Endi platforma bildirishnomalari (vazifalar, muddatlar, "
                    "tasdiqlashlar) shu yerga keladi."
                )
            else:
                await update.message.reply_text("Token yaroqsiz yoki muddati o'tgan.")

        @sync_to_async
        def _unlink(chat_id):
            from apps.accounts.models import User
            User.objects.filter(telegram_chat_id=str(chat_id)).update(telegram_chat_id=None)

        async def unlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
            await _unlink(update.effective_chat.id)
            await update.message.reply_text("Hisobingiz uzildi.")

        @sync_to_async
        def _record_event(chat_id, text):
            from apps.accounts.models import User
            from apps.telegram_bot.models import TelegramEvent

            text = text or ""
            user = User.objects.filter(telegram_chat_id=str(chat_id)).first()
            kind = TelegramEvent.Kind.COMMAND if text.startswith("/") else TelegramEvent.Kind.MESSAGE
            TelegramEvent.objects.create(user=user, chat_id=str(chat_id), kind=kind, text=text)

        async def record_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if update.effective_chat and update.effective_message:
                await _record_event(update.effective_chat.id, update.effective_message.text)

        async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = await _get_user_by_chat_id(update.effective_chat.id)
            prefix = f"[{user.full_name}] " if user else ""
            await update.message.reply_text(f"{prefix}{update.message.text}")

        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        # group=-1: barcha xabar/buyruqlarni asosiy handlerlardan oldin jurnalga
        # yozadi, ularning ishlashiga xalaqit bermaydi.
        application.add_handler(TypeHandler(Update, record_update), group=-1)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_cmd))
        application.add_handler(CommandHandler("whoami", whoami))
        application.add_handler(CommandHandler("myinfo", whoami))
        application.add_handler(CommandHandler("miniapp", miniapp))
        application.add_handler(CommandHandler("link", link))
        application.add_handler(CommandHandler("unlink", unlink))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

        self.stdout.write(self.style.SUCCESS("Starting Telegram bot (long polling)..."))
        application.run_polling()
