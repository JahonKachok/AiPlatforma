import asyncio
import time
from html import escape

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.validators import AllowedExtensionsValidator
from apps.telegram_bot.texts import LANGUAGE_LABELS, all_menu_labels, menu_key_for, t


class Command(BaseCommand):
    help = "Runs the Telegram bot in long-polling mode (separate long-running process)."

    # Token admin paneldan (core:integration_settings) yoki .env dan olinadi.
    # Bot shu oraliqda tokenni tekshiradi: o'zgarsa — yangi token bilan qayta
    # ishga tushadi, jarayonni qo'lda qayta yoqish shart emas.
    TOKEN_POLL_SECONDS = 30

    def handle(self, *args, **options):
        import time

        from telegram.error import InvalidToken

        from apps.core.runtime_config import get_config

        reported = None
        while True:
            token = get_config("TELEGRAM_BOT_TOKEN")
            if not token or token == reported:
                if reported is None:
                    self.stderr.write(self.style.WARNING(
                        "TELEGRAM_BOT_TOKEN is not configured — waiting for it "
                        "(admin panel → Integrations, or .env)."
                    ))
                    reported = token
                time.sleep(self.TOKEN_POLL_SECONDS)
                continue
            reported = None
            try:
                restart = self._run_bot(token)
            except InvalidToken:
                self.stderr.write(self.style.ERROR(
                    "Telegram rejected the bot token — waiting for a new one."
                ))
                reported = token
                continue
            if not restart:
                return
            self.stdout.write(self.style.WARNING("Bot token changed — restarting..."))

    def _run_bot(self, token):
        """Botni ishga tushiradi. True — token o'zgargani uchun to'xtatildi
        (qayta ishga tushirish kerak), False — oddiy to'xtatish (Ctrl+C)."""
        from apps.core.runtime_config import get_config

        restart = {"requested": False}

        from django.core.exceptions import ValidationError
        from django.core.files.base import ContentFile
        from telegram import (
            BotCommand,
            InlineKeyboardButton,
            InlineKeyboardMarkup,
            InputFile,
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

        def _is_manager(user) -> bool:
            from apps.accounts.models import User
            return user is not None and (
                user.is_superuser or user.role in (User.Role.ADMIN, User.Role.MANAGER)
            )

        def main_keyboard(lang, is_manager=False):
            rows = [
                [t("menu.profile", lang), t("menu.upload", lang)],
                [t("menu.help", lang), t("menu.settings", lang)],
            ]
            if is_manager:
                rows.insert(0, [t("menu.report", lang)])
            return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)

        def language_keyboard(prefix="setlang"):
            return InlineKeyboardMarkup([
                [InlineKeyboardButton(label, callback_data=f"{prefix}:{code}")]
                for code, label in LANGUAGE_LABELS.items()
            ])

        async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
            args = context.args
            if args and args[0].startswith("link_"):
                await link(update, context, token=args[0][len("link_"):])
                return
            lang = await get_lang(update, context)
            await update.message.reply_html(
                t("start", lang), reply_markup=language_keyboard("startlang")
            )

        async def start_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """/start ostidagi til tugmasi: tilni saqlab, xabarni shu tilda
            qayta chizadi va pastki menyuni yangi tilda o'rnatadi."""
            query = update.callback_query
            await query.answer()
            lang = query.data.split(":", 1)[1]
            if lang not in LANGUAGE_LABELS:
                return
            current = await get_lang(update, context)
            await _set_chat_lang(update.effective_chat.id, lang)
            context.user_data["lang"] = lang
            if lang != current:  # bir xil matnni edit qilish Telegram'da xato beradi
                await query.edit_message_text(
                    t("start", lang), parse_mode="HTML",
                    reply_markup=language_keyboard("startlang"),
                )
            user = await _get_user_by_chat_id(update.effective_chat.id)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=t("settings.language_saved", lang),
                reply_markup=main_keyboard(lang, _is_manager(user)),
            )

        async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
            lang = await get_lang(update, context)
            await update.message.reply_html(t("help", lang))

        @sync_to_async
        def _get_user_by_chat_id(chat_id):
            from apps.accounts.models import User
            return User.objects.filter(telegram_chat_id=str(chat_id), is_active=True).first()

        async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = await _get_user_by_chat_id(update.effective_chat.id)
            if user:
                await update.message.reply_html(
                    f"<b>{escape(user.full_name)}</b>\n{escape(user.email)}\n{user.get_role_display()}"
                )
            else:
                lang = await get_lang(update, context)
                await update.message.reply_text(t("not_linked", lang))

        @sync_to_async
        def _do_link(token, chat_id):
            from apps.accounts.models import User
            from apps.telegram_bot.models import TelegramLinkToken

            link_token = TelegramLinkToken.objects.filter(token=token).first()
            if not link_token or not link_token.is_valid() or not link_token.user.is_active:
                return None
            user = link_token.user
            # Bitta chat — bitta hisob: aks holda bot qaysi foydalanuvchi
            # nomidan ishlashi (va kimning bildirishnomalari kelishi) noaniq.
            User.objects.filter(telegram_chat_id=str(chat_id)).exclude(pk=user.pk).update(
                telegram_chat_id=None
            )
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
                      name=escape(user.full_name), role=user.get_role_display(),
                      email=escape(user.email)),
                    reply_markup=main_keyboard(lang, _is_manager(user)),
                )
                from apps.pult.dispatcher import kpi_rules

                await update.message.reply_html(await sync_to_async(kpi_rules)(lang))
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
            user = User.objects.filter(telegram_chat_id=str(chat_id), is_active=True).first()
            kind = TelegramEvent.Kind.COMMAND if text.startswith("/") else TelegramEvent.Kind.MESSAGE
            TelegramEvent.objects.create(user=user, chat_id=str(chat_id), kind=kind, text=text)

        async def record_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if update.effective_chat and update.effective_message:
                message = update.effective_message
                text = message.text or message.caption
                if not text and message.voice:
                    text = f"[ovozli xabar, {message.voice.duration}s]"
                await _record_event(update.effective_chat.id, text)

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
                await query.edit_message_text(
                    t("settings.choose_language", lang),
                    reply_markup=language_keyboard("setlang"),
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
            user = await _get_user_by_chat_id(update.effective_chat.id)
            # Pastki menyu tugmalari yangi tilda qayta chiziladi.
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=t("settings.title", lang),
                reply_markup=main_keyboard(lang, _is_manager(user)),
            )

        @sync_to_async
        def _run_deadline_report():
            from apps.ai_agents import services
            return services.run_deadline_agent()

        async def ai_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Admin/menejer uchun bir tugmalik AI muddat-hisoboti."""
            lang = await get_lang(update, context)
            user = await _get_user_by_chat_id(update.effective_chat.id)
            if user is None:
                await update.message.reply_text(t("not_linked", lang))
                return
            if not _is_manager(user):
                await update.message.reply_text(t("report.admins_only", lang))
                return
            await update.message.reply_text(t("report.generating", lang))
            await update.effective_chat.send_action("typing")
            try:
                report = await _run_deadline_report()
            except Exception:
                await update.message.reply_text(t("ai.error", lang))
                raise
            await update.message.reply_text(report or t("report.empty", lang))

        async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Pastki menyu tugmalarini tegishli buyruqlarga yo'naltiradi."""
            key = menu_key_for(update.message.text)
            if key == "menu.profile":
                await whoami(update, context)
            elif key == "menu.help":
                await help_cmd(update, context)
            elif key == "menu.settings":
                await settings_menu(update, context)
            elif key == "menu.report":
                await ai_report(update, context)
            elif key == "menu.upload":
                lang = await get_lang(update, context)
                await update.message.reply_text(t("upload.hint", lang))

        # --- Fayl/hujjat qabul qilish (barcha ulangan foydalanuvchilar
        #     uchun — saytdagi hujjat yuklash bilan bir xil: ko'rinadigan
        #     loyihalardan biriga yuklash mumkin, rol cheklovi yo'q) --------

        @sync_to_async
        def _get_uploader(chat_id):
            """Fayl yuklay oladigan foydalanuvchi va uning ko'rinadigan
            loyihalarini qaytaradi. (None, None) — hisob ulanmagan."""
            from apps.accounts.models import User
            from apps.projects.permissions import visible_projects_for

            user = User.objects.filter(telegram_chat_id=str(chat_id), is_active=True).first()
            if user is None:
                return None, None
            projects = list(visible_projects_for(user).order_by("-created_at").values_list("id", "name")[:20])
            return user, projects

        @sync_to_async
        def _save_document(chat_id, project_id, pending, data):
            from django.core.exceptions import ValidationError
            from django.core.files.base import ContentFile

            from apps.accounts.models import User
            from apps.core.validators import AllowedExtensionsValidator
            from apps.documents.models import AuditLog, Document, DocumentVersion
            from apps.projects.permissions import visible_projects_for

            user = User.objects.filter(telegram_chat_id=str(chat_id), is_active=True).first()
            if user is None:
                return None
            # callback_data mijoz tomonidan soxtalashtirilishi mumkin, shuning
            # uchun loyiha yana foydalanuvchi ko'ra oladiganlar ichidan olinadi.
            try:
                project = visible_projects_for(user).filter(pk=project_id).first()
            except ValidationError:  # UUID bo'lmagan qiymat
                return None
            if project is None:
                return None
            # Saytdagi yuklash bilan bir xil oq ro'yxat (.html/.svg va h.k. yo'q).
            try:
                AllowedExtensionsValidator()(ContentFile(b"", name=pending["file_name"]))
            except ValidationError:
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
            document.original_name = pending["file_name"][:255]
            document.save()
            DocumentVersion.objects.create(
                document=document, version_number=document.version,
                file=document.file.name, file_size=document.file_size, uploaded_by=user,
            )
            AuditLog.log(obj=document, action="uploaded", user=user, details={"source": "telegram"})
            return document

        async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Yuborilgan fayl/rasmni qabul qilib, loyiha tanlashni so'raydi."""
            message = update.message
            lang = await get_lang(update, context)
            from apps.ai_agents.secretary import SIGN_CAPTION

            if message.document and SIGN_CAPTION.search(message.caption or ""):
                # «imzola» izohli PDF — direktor tasdig'iga (Sekretar).
                from apps.ai_agents import secretary

                user = await _get_user_by_chat_id(update.effective_chat.id)
                if user is None:
                    await message.reply_text(t("not_linked", lang))
                    return
                tg_file = await context.bot.get_file(message.document.file_id)
                data = await tg_file.download_as_bytearray()
                reply = await sync_to_async(secretary.submit_pdf)(
                    user, message.document.file_name or "document.pdf", data, lang)
                await message.reply_text(reply.text)
                return
            wait = _take_wait(context, "mid") if message.document else None
            if wait:
                from apps.pult import dispatcher

                attachment = message.document
                if attachment.file_size and attachment.file_size > dispatcher.FILE_LIMIT:
                    await message.reply_text(t("pd.file_bad", lang))
                    return
                tg_file = await context.bot.get_file(attachment.file_id)
                data = await tg_file.download_as_bytearray()
                reply = await sync_to_async(dispatcher.handle_file)(
                    update.effective_chat.id, wait, attachment.file_name or "file.bin", data, attachment.mime_type or "")
                await _send_reply(update.effective_chat, reply, context)
                return
            user, projects = await _get_uploader(update.effective_chat.id)
            if user is None:
                await message.reply_text(t("not_linked", lang))
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

            # Ruxsat etilmagan turni loyiha so'ralmasdan oldin rad etamiz
            # (_save_document'dagi tekshiruv — callback soxtalashtirilsa ham).
            validator = AllowedExtensionsValidator()
            try:
                validator(ContentFile(b"", name=file_name))
            except ValidationError:
                await message.reply_text(
                    t("upload.bad_type", lang, allowed=", ".join(validator.allowed))
                )
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
                t("upload.choose_project", lang, caption=escape(caption)),
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
                  name=escape(document.name), project=escape(document.project.name),
                  url=f"{settings.FRONTEND_URL}/documents/{document.pk}/"),
                parse_mode="HTML",
            )

        # ai_chat holatlari uchun ichki belgilar (sentinel qiymatlar)
        AI_NOT_LINKED, AI_NOT_CONFIGURED, AI_RATE_LIMITED = "not_linked", "not_configured", "rate_limited"

        @sync_to_async
        def _ai_answer(chat_id, text, lang, history, audio=None):
            from apps.accounts.models import User
            from apps.ai_agents import services

            user = User.objects.filter(telegram_chat_id=str(chat_id), is_active=True).first()
            if user is None:
                return AI_NOT_LINKED, "", [], []
            if not services.is_configured():
                return AI_NOT_CONFIGURED, "", [], []
            if services.rate_limited(user):
                return AI_RATE_LIMITED, "", [], []
            proposals = []
            answer, documents = services.answer_telegram(user, text, lang=lang, history=history,
                                                         audio=audio, proposals=proposals)
            if proposals:
                return "ok", proposals[0].text, documents, proposals[0].buttons
            return "ok", answer, documents, []

        # AI qidiruvida topilgan hujjatlardan chatga avtomatik yuboriladigan
        # eng ko'p soni — Telegram'ni fayllar bilan to'ldirib yubormaslik uchun.
        MAX_AUTO_SENT_DOCUMENTS = 5

        @sync_to_async
        def _read_document_file(doc_id):
            from apps.documents.models import Document

            doc = Document.objects.filter(pk=doc_id).first()
            if doc is None or not doc.file:
                return None
            from apps.documents.archivist import open_file
            from apps.documents.services import file_basename

            try:
                with open_file(doc) as f:
                    data = f.read()
            except FileNotFoundError:
                return None
            file_name = file_basename(doc)
            return data, file_name, doc.name

        async def _send_found_documents(update: Update, documents):
            """AI find_documents orqali topgan hujjat fayllarini haqiqiy
            Telegram-fayl sifatida yuboradi (matnli javobdan keyin)."""
            for item in documents[:MAX_AUTO_SENT_DOCUMENTS]:
                result = await _read_document_file(item["id"])
                if not result:
                    continue
                data, file_name, doc_name = result
                await update.effective_chat.send_document(
                    document=InputFile(bytes(data), filename=file_name),
                    caption=doc_name[:1024],
                )

        # --- Pult dispetcheri (apps/pult/dispatcher.py) ----------------------

        def _markup(buttons):
            if not buttons:
                return None
            return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=data) for label, data in row]
                                         for row in buttons])

        PD_WAIT_SECONDS = 30 * 60

        def _take_wait(context, kind):
            """Bot kutayotgan javob (rad etish sababi / oraliq fayl), 30 daqiqagacha."""
            wait = context.user_data.get("pd_wait")
            if not wait or wait.get("a") != kind:
                return None
            context.user_data.pop("pd_wait", None)
            return wait if time.monotonic() - wait.get("at", 0) < PD_WAIT_SECONDS else None

        async def _send_reply(chat, reply, context):
            if reply.wait:
                context.user_data["pd_wait"] = {**reply.wait, "at": time.monotonic()}
            await chat.send_message(reply.text, reply_markup=_markup(reply.buttons))

        async def pd_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Pult tugmalari: qabul/rad, foiz, topshirish, oraliq fayl."""
            from apps.pult import dispatcher

            query = update.callback_query
            await query.answer()
            reply = await sync_to_async(dispatcher.handle_callback)(update.effective_chat.id, query.data)
            try:
                await query.edit_message_reply_markup(reply_markup=None)  # bir marta bosiladi
            except Exception:
                pass
            if query.data.startswith("pd:m:"):
                context.user_data.pop("pd_wait", None)
            await _send_reply(update.effective_chat, reply, context)

        async def pd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """/report — faol vazifalar bo'yicha foiz tugmalari."""
            from apps.pult import dispatcher

            lang = await get_lang(update, context)
            user = await _get_user_by_chat_id(update.effective_chat.id)
            if user is None:
                await update.message.reply_text(t("not_linked", lang))
                return
            workflows = await sync_to_async(dispatcher.active_for)(user)
            if not workflows:
                await update.message.reply_text(t("pd.no_active", lang))
                return
            for wf in workflows[:10]:
                await update.message.reply_text(
                    t("pd.report_ask", lang, n=wf.number, title=wf.task.title, pct=round(wf.done * 100)),
                    reply_markup=_markup(dispatcher.percent_buttons(wf)),
                )

        async def pd_kpi(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """/kpi — oylik ball, reytingdagi o'rin va qoidalar."""
            from apps.pult import dispatcher

            lang = await get_lang(update, context)
            user = await _get_user_by_chat_id(update.effective_chat.id)
            if user is None:
                await update.message.reply_text(t("not_linked", lang))
                return
            await update.message.reply_html(await sync_to_async(dispatcher.kpi_summary)(user, lang))

        # --- Orchestrator (apps/ai_agents/orchestrator.py) -------------------

        @sync_to_async
        def _orchestrator_reply(chat_id, text, lang):
            from apps.ai_agents import orchestrator

            user = _user_by_chat_sync(chat_id)
            if user is None:
                return None
            return orchestrator.handle(user, text, lang)

        def _user_by_chat_sync(chat_id):
            from apps.accounts.models import User
            return User.objects.filter(telegram_chat_id=str(chat_id), is_active=True).first()

        async def _orchestrate(update, context, text, lang):
            """True — xabarni agent bajardi (chat'ga berilmaydi)."""
            reply = await _orchestrator_reply(update.effective_chat.id, text, lang)
            if reply is None:
                return False
            await update.effective_chat.send_message(
                reply.text, parse_mode="HTML" if reply.html else None, reply_markup=_markup(reply.buttons))
            return True

        async def ag_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Agent amalini tasdiqlash/bekor qilish (moliya yozuvi)."""
            from apps.ai_agents import orchestrator

            query = update.callback_query
            await query.answer()
            lang = await get_lang(update, context)
            user = await sync_to_async(_user_by_chat_sync)(update.effective_chat.id)
            reply = await sync_to_async(orchestrator.confirm)(user, query.data, lang)
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            await update.effective_chat.send_message(reply.text)

        async def sg_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Direktor: hujjatga imzo va muhr qo'yish yoki rad etish."""
            from apps.ai_agents import secretary

            query = update.callback_query
            await query.answer()
            lang = await get_lang(update, context)
            user = await sync_to_async(_user_by_chat_sync)(update.effective_chat.id)
            try:
                await query.edit_message_reply_markup(reply_markup=None)
            except Exception:
                pass
            reply = await sync_to_async(secretary.decide)(user, query.data, lang)
            await update.effective_chat.send_message(reply.text)

        async def ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Oddiy matnli xabarlarga platforma konteksti asosida AI javob beradi.

            Oxirgi almashinuvlar user_data'da saqlanadi — AI "uni", "o'sha
            loyihani" kabi murojaatlarni tushunadi (bot qayta ishga
            tushirilganda tarix tozalanadi)."""
            lang = await get_lang(update, context)
            text = update.message.text or ""
            wait = _take_wait(context, "decline") or _take_wait(context, "terms")
            if wait:
                from apps.pult import dispatcher

                reply = await sync_to_async(dispatcher.handle_text)(update.effective_chat.id, wait, text)
                await _send_reply(update.effective_chat, reply, context)
                return
            if await _orchestrate(update, context, text, lang):
                return
            history = context.user_data.get("ai_history", [])
            await update.effective_chat.send_action("typing")
            try:
                state, answer, documents, buttons = await _ai_answer(update.effective_chat.id, text, lang, history)
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
                history.extend([("user", text), ("assistant", answer)])
                context.user_data["ai_history"] = history[-8:]
                await update.message.reply_text(answer, reply_markup=_markup(buttons))
                if documents:
                    await _send_found_documents(update, documents)

        VOICE_MAX_SECONDS = 180  # 3 daqiqa

        async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Ovozli xabarni Gemini'ga uzatib, AI javobini qaytaradi."""
            lang = await get_lang(update, context)
            voice = update.message.voice
            if voice.duration and voice.duration > VOICE_MAX_SECONDS:
                await update.message.reply_text(t("voice.too_long", lang))
                return
            history = context.user_data.get("ai_history", [])
            await update.effective_chat.send_action("typing")
            from apps.ai_agents.services import transcribe
            from apps.core.runtime_config import get_config as _cfg

            if not await sync_to_async(_cfg)("GEMINI_API_KEY"):
                # Claude audio eshitmaydi — javobni to'qib chiqarmasin.
                await update.message.reply_text(t("ag.voice_needs_gemini", lang))
                return
            try:
                tg_file = await context.bot.get_file(voice.file_id)
                data = bytes(await tg_file.download_as_bytearray())
                # Avval matnga: keyin Orchestrator (pul, ZIP, KPI) yoki oddiy chat —
                # audio modelga ikkinchi marta yuborilmaydi.
                transcript = await sync_to_async(transcribe)((data, voice.mime_type or "audio/ogg"))
                if transcript:
                    if await _orchestrate(update, context, transcript, lang):
                        return
                    state, answer, documents, buttons = await _ai_answer(update.effective_chat.id, transcript, lang, history)
                else:
                    state, answer, documents, buttons = await _ai_answer(
                        update.effective_chat.id, "", lang, history, audio=(data, voice.mime_type or "audio/ogg"))
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
                history.extend([("user", f"[ovozli xabar, {voice.duration}s]"), ("assistant", answer)])
                context.user_data["ai_history"] = history[-8:]
                await update.message.reply_text(answer, reply_markup=_markup(buttons))
                if documents:
                    await _send_found_documents(update, documents)

        async def post_init(app):
            # Telegram'ning chap pastki "Menu" tugmasidagi buyruqlar ro'yxati —
            # har bir interfeys tili uchun alohida o'rnatiladi.
            commands = {
                None: [  # standart (til aniqlanmaganda)
                    ("start", "Botni ishga tushirish"), ("whoami", "Profil ma'lumotlari"),
                    ("report", "Kunlik hisobot (foiz)"), ("kpi", "KPI ballarim"),
                    ("link", "Hisobni ulash"), ("unlink", "Hisobni uzish"),
                    ("help", "Yordam"),
                ],
                "ru": [
                    ("start", "Запустить бота"), ("whoami", "Данные профиля"),
                    ("report", "Ежедневный отчёт (%)"), ("kpi", "Мои баллы KPI"),
                    ("link", "Привязать аккаунт"), ("unlink", "Отвязать аккаунт"),
                    ("help", "Помощь"),
                ],
                "en": [
                    ("start", "Start the bot"), ("whoami", "Profile info"),
                    ("report", "Daily report (%)"), ("kpi", "My KPI points"),
                    ("link", "Link account"), ("unlink", "Unlink account"),
                    ("help", "Help"),
                ],
            }
            for language_code, items in commands.items():
                await app.bot.set_my_commands(
                    [BotCommand(name, desc) for name, desc in items],
                    language_code=language_code,
                )

        async def watch_token(app):
            while True:
                await asyncio.sleep(self.TOKEN_POLL_SECONDS)
                try:
                    current = await sync_to_async(get_config)("TELEGRAM_BOT_TOKEN")
                except Exception:
                    continue
                if current != token:
                    restart["requested"] = True
                    app.stop_running()
                    return

        async def post_init_with_watch(app):
            await post_init(app)
            app.create_task(watch_token(app))

        application = (
            Application.builder().token(token).post_init(post_init_with_watch).build()
        )
        # group=-1: barcha xabar/buyruqlarni asosiy handlerlardan oldin jurnalga
        # yozadi, ularning ishlashiga xalaqit bermaydi.
        application.add_handler(TypeHandler(Update, record_update), group=-1)
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_cmd))
        application.add_handler(CommandHandler("whoami", whoami))
        application.add_handler(CommandHandler("myinfo", whoami))
        application.add_handler(CommandHandler("link", link))
        application.add_handler(CommandHandler("unlink", unlink))
        application.add_handler(CommandHandler("report", pd_report))
        application.add_handler(CommandHandler("kpi", pd_kpi))
        application.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, receive_file))
        application.add_handler(MessageHandler(filters.VOICE, voice_message))
        application.add_handler(CallbackQueryHandler(choose_project, pattern=r"^tgdoc:"))
        application.add_handler(CallbackQueryHandler(pd_callback, pattern=r"^pd:"))
        application.add_handler(CallbackQueryHandler(ag_callback, pattern=r"^ag:"))
        application.add_handler(CallbackQueryHandler(sg_callback, pattern=r"^sg:"))
        application.add_handler(CallbackQueryHandler(settings_callback, pattern=r"^settings:"))
        application.add_handler(CallbackQueryHandler(set_language, pattern=r"^setlang:"))
        application.add_handler(CallbackQueryHandler(start_language, pattern=r"^startlang:"))
        # Menyu tugmalari ai_chat'dan oldin turishi shart — aks holda tugma
        # matni AI'ga oddiy savol sifatida ketadi.
        application.add_handler(MessageHandler(filters.Text(all_menu_labels()), menu_router))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ai_chat))

        self.stdout.write(self.style.SUCCESS("Starting Telegram bot (long polling)..."))
        # Python 3.14 removed the implicit event-loop creation that
        # application.run_polling() relies on internally — create one explicitly.
        asyncio.set_event_loop(asyncio.new_event_loop())
        application.run_polling()
        return restart["requested"]
