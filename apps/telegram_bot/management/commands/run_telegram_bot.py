from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.telegram_bot.texts import LANGUAGE_LABELS, all_menu_labels, menu_key_for, t


class Command(BaseCommand):
    help = "Runs the Telegram bot in long-polling mode (separate long-running process)."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stderr.write(self.style.ERROR("TELEGRAM_BOT_TOKEN is not configured."))
            return

        from telegram import (
            BotCommand,
            InlineKeyboardButton,
            InlineKeyboardMarkup,
            ReplyKeyboardMarkup,
            Update,
        )
        from telegram.ext import (
            Application,
            CallbackQueryHandler,
            CommandHandler,
            ContextTypes,
            MessageHandler,
            TypeHandler,
            filters,
        )

        # --- Til ------------------------------------------------------------

        @sync_to_async
        def _get_chat_lang(chat_id):
            from apps.telegram_bot.models import TelegramChat

            chat = TelegramChat.objects.filter(chat_id=str(chat_id)).first()
            return chat.language if chat else "uz"

        @sync_to_async
        def _set_chat_lang(chat_id, lang):
            from apps.telegram_bot.models import TelegramChat

            TelegramChat.objects.update_or_create(
                chat_id=str(chat_id), defaults={"language": lang}
            )

        async def get_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Chat tilini qaytaradi (user_data'da keshlanadi)."""
            lang = context.user_data.get("lang")
            if not lang:
                lang = await _get_chat_lang(update.effective_chat.id)
                context.user_data["lang"] = lang
            return lang

        # --- Doimiy pastki menyu tugmalari -----------------------------------

        def main_keyboard(lang):
            return ReplyKeyboardMarkup(
                [
                    [t("menu.profile", lang), t("menu.miniapp", lang)],
                    [t("menu.upload", lang), t("menu.help", lang)],
                    [t("menu.settings", lang)],
                ],
                resize_keyboard=True,
                is_persistent=True,
            )

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            args = context.args
            if args and args[0].startswith("link_"):
                await link(update, context, token=args[0][len("link_"):])
                return
            lang = await get_lang(update, context)
            await update.message.reply_html(t("start", lang), reply_markup=main_keyboard(lang))

        async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            lang = await get_lang(update, context)
            await update.message.reply_html(t("help", lang))

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
                lang = await get_lang(update, context)
                await update.message.reply_text(t("not_linked", lang))

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
            lang = await get_lang(update, context)
            token = token or (context.args[0] if context.args else None)
            if not token:
                await update.message.reply_text(t("link.usage", lang))
                return
            user = await _do_link(token, update.effective_chat.id)
            if user:
                await update.message.reply_html(
                    t("link.success", lang,
                      name=user.full_name, role=user.get_role_display(), email=user.email),
                    reply_markup=main_keyboard(lang),
                )
            else:
                await update.message.reply_text(t("link.invalid", lang))

        @sync_to_async
        def _unlink(chat_id):
            from apps.accounts.models import User
            User.objects.filter(telegram_chat_id=str(chat_id)).update(telegram_chat_id=None)

        async def unlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
            lang = await get_lang(update, context)
            await _unlink(update.effective_chat.id)
            await update.message.reply_text(t("unlinked", lang))

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
                message = update.effective_message
                await _record_event(update.effective_chat.id, message.text or message.caption)

        # --- Sozlamalar -------------------------------------------------------

        async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
            lang = await get_lang(update, context)
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton(t("settings.language_btn", lang), callback_data="settings:lang")
            ]])
            await update.message.reply_text(t("settings.title", lang), reply_markup=keyboard)

        async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            lang = await get_lang(update, context)
            if query.data == "settings:lang":
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(label, callback_data=f"setlang:{code}")]
                    for code, label in LANGUAGE_LABELS.items()
                ])
                await query.edit_message_text(
                    t("settings.choose_language", lang), reply_markup=keyboard
                )

        async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            lang = query.data.split(":", 1)[1]
            if lang not in LANGUAGE_LABELS:
                return
            await _set_chat_lang(update.effective_chat.id, lang)
            context.user_data["lang"] = lang
            await query.edit_message_text(t("settings.language_saved", lang))
            # Pastki menyu tugmalari yangi tilda qayta chiziladi.
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=t("settings.title", lang),
                reply_markup=main_keyboard(lang),
            )

        async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Pastki menyu tugmalarini tegishli buyruqlarga yo'naltiradi."""
            key = menu_key_for(update.message.text)
            if key == "menu.profile":
                await whoami(update, context)
            elif key == "menu.miniapp":
                await miniapp(update, context)
            elif key == "menu.help":
                await help_cmd(update, context)
            elif key == "menu.settings":
                await settings_menu(update, context)
            elif key == "menu.upload":
                lang = await get_lang(update, context)
                await update.message.reply_text(t("upload.hint", lang))

        # --- Fayl/hujjat qabul qilish (adminlar uchun) --------------------

        @sync_to_async
        def _get_uploader(chat_id):
            """Fayl yuklashga ruxsati bor foydalanuvchini qaytaradi.

            (user, projects) — ruxsat bor; (user, None) — rol yetarli emas;
            (None, None) — hisob ulanmagan."""
            from apps.accounts.models import User
            from apps.projects.permissions import visible_projects_for

            user = User.objects.filter(telegram_chat_id=str(chat_id)).first()
            if user is None:
                return None, None
            if not (user.is_superuser or user.role in (User.Role.ADMIN, User.Role.MANAGER)):
                return user, None
            projects = list(visible_projects_for(user).order_by("-created_at").values_list("id", "name")[:20])
            return user, projects

        @sync_to_async
        def _save_document(chat_id, project_id, pending, data):
            from django.core.files.base import ContentFile

            from apps.accounts.models import User
            from apps.documents.models import AuditLog, Document, DocumentVersion
            from apps.projects.models import Project

            user = User.objects.filter(telegram_chat_id=str(chat_id)).first()
            project = Project.objects.filter(pk=project_id).first()
            if user is None or project is None:
                return None
            document = Document(
                name=pending["caption"][:255],
                doc_type="telegram",
                project=project,
                uploaded_by=user,
                file_size=len(data),
                mime_type=pending.get("mime_type") or "",
            )
            document.file.save(pending["file_name"], ContentFile(bytes(data)), save=False)
            document.save()
            DocumentVersion.objects.create(
                document=document, version_number=document.version,
                file=document.file.name, file_size=document.file_size, uploaded_by=user,
            )
            AuditLog.log(obj=document, action="uploaded", user=user, details={"source": "telegram"})
            return document

        async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Admin yuborgan fayl/rasmni qabul qilib, loyiha tanlashni so'raydi."""
            message = update.message
            lang = await get_lang(update, context)
            user, projects = await _get_uploader(update.effective_chat.id)
            if user is None:
                await message.reply_text(t("not_linked", lang))
                return
            if projects is None:
                await message.reply_text(t("upload.admins_only", lang))
                return
            if not projects:
                await message.reply_text(t("upload.no_projects", lang))
                return

            caption = (message.caption or "").strip()
            if not caption:
                await message.reply_text(t("upload.caption_required", lang))
                return

            if message.document:
                attachment = message.document
                file_name = attachment.file_name or f"{caption[:50]}.bin"
                mime_type = attachment.mime_type or ""
            else:  # photo — eng katta o'lchamini olamiz
                attachment = message.photo[-1]
                file_name = f"{caption[:50]}.jpg"
                mime_type = "image/jpeg"

            if attachment.file_size and attachment.file_size > 20 * 1024 * 1024:
                await message.reply_text(t("upload.too_big", lang))
                return

            context.user_data["pending_doc"] = {
                "file_id": attachment.file_id,
                "file_name": file_name,
                "mime_type": mime_type,
                "caption": caption,
            }
            keyboard = [
                [InlineKeyboardButton(name[:60], callback_data=f"tgdoc:{pid}")]
                for pid, name in projects
            ]
            keyboard.append(
                [InlineKeyboardButton(t("upload.cancel", lang), callback_data="tgdoc:cancel")]
            )
            await message.reply_text(
                t("upload.choose_project", lang, caption=caption),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )

        async def choose_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
            query = update.callback_query
            await query.answer()
            lang = await get_lang(update, context)
            if query.data == "tgdoc:cancel":
                context.user_data.pop("pending_doc", None)
                await query.edit_message_text(t("upload.cancelled", lang))
                return

            pending = context.user_data.get("pending_doc")
            if not pending:
                await query.edit_message_text(t("upload.expired", lang))
                return

            project_id = query.data.split(":", 1)[1]
            await query.edit_message_text(t("upload.downloading", lang))
            try:
                tg_file = await context.bot.get_file(pending["file_id"])
                data = await tg_file.download_as_bytearray()
            except Exception:
                await query.edit_message_text(t("upload.download_error", lang))
                raise
            document = await _save_document(update.effective_chat.id, project_id, pending, data)
            context.user_data.pop("pending_doc", None)
            if document is None:
                await query.edit_message_text(t("upload.save_error", lang))
                return
            await query.edit_message_text(
                t("upload.saved", lang,
                  name=document.name, project=document.project.name,
                  url=f"{settings.FRONTEND_URL}/documents/{document.pk}/"),
                parse_mode="HTML",
            )

        # ai_chat holatlari uchun ichki belgilar (sentinel qiymatlar)
        AI_NOT_LINKED, AI_NOT_CONFIGURED, AI_RATE_LIMITED = "not_linked", "not_configured", "rate_limited"

        @sync_to_async
        def _ai_answer(chat_id, text, lang):
            from apps.accounts.models import User
            from apps.ai_agents import services

            user = User.objects.filter(telegram_chat_id=str(chat_id)).first()
            if user is None:
                return AI_NOT_LINKED, ""
            if not services.is_configured():
                return AI_NOT_CONFIGURED, ""
            if services.rate_limited(user):
                return AI_RATE_LIMITED, ""
            return "ok", services.answer_telegram(user, text, lang=lang)

        async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Oddiy matnli xabarlarga platforma konteksti asosida AI javob beradi."""
            lang = await get_lang(update, context)
            await update.effective_chat.send_action("typing")
            try:
                state, answer = await _ai_answer(update.effective_chat.id, update.message.text or "", lang)
            except Exception:
                await update.message.reply_text(t("ai.error", lang))
                raise
            if state == AI_NOT_LINKED:
                await update.message.reply_text(t("ai.not_linked", lang))
            elif state == AI_RATE_LIMITED:
                await update.message.reply_text(t("ai.rate_limited", lang))
            elif state == AI_NOT_CONFIGURED or not answer:
                await update.message.reply_text(t("ai.not_configured", lang))
            else:
                await update.message.reply_text(answer)

        async def post_init(app):
            # Telegram'ning chap pastki "Menu" tugmasidagi buyruqlar ro'yxati —
            # har bir interfeys tili uchun alohida o'rnatiladi.
            commands = {
                None: [  # standart (til aniqlanmaganda)
                    ("start", "Botni ishga tushirish"), ("whoami", "Profil ma'lumotlari"),
                    ("miniapp", "Veb-ilova havolasi"), ("link", "Hisobni ulash"),
                    ("unlink", "Hisobni uzish"), ("help", "Yordam"),
                ],
                "ru": [
                    ("start", "Запустить бота"), ("whoami", "Данные профиля"),
                    ("miniapp", "Ссылка на веб-приложение"), ("link", "Привязать аккаунт"),
                    ("unlink", "Отвязать аккаунт"), ("help", "Помощь"),
                ],
                "en": [
                    ("start", "Start the bot"), ("whoami", "Profile info"),
                    ("miniapp", "Web app link"), ("link", "Link account"),
                    ("unlink", "Unlink account"), ("help", "Help"),
                ],
            }
            for language_code, items in commands.items():
                await app.bot.set_my_commands(
                    [BotCommand(name, desc) for name, desc in items],
                    language_code=language_code,
                )

        application = (
            Application.builder().token(settings.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
        )
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
        application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, receive_file))
        application.add_handler(CallbackQueryHandler(choose_project, pattern=r"^tgdoc:"))
        application.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^settings:"))
        application.add_handler(CallbackQueryHandler(set_language, pattern=r"^setlang:"))
        # Menyu tugmalari ai_chat'dan oldin turishi shart — aks holda tugma
        # matni AI'ga oddiy savol sifatida ketadi.
        application.add_handler(MessageHandler(filters.Text(all_menu_labels()), menu_router))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))

        self.stdout.write(self.style.SUCCESS("Starting Telegram bot (long polling)..."))
        application.run_polling()
