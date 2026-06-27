import logging
import json
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from app.config import settings
from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.telegram_linking import link_telegram_account
from sqlalchemy import select

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self):
        self.app: Optional[Application] = None
        self.enabled = False
        self.user_id = settings.TELEGRAM_USER_ID
        self.polling_task = None

    async def initialize(self):
        """Initialize Telegram bot with webhooks or polling"""
        if not settings.TELEGRAM_BOT_TOKEN:
            logger.info("Telegram bot token not configured")
            return

        try:
            self.app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

            self.app.add_handler(CommandHandler("start", self.start_command))
            self.app.add_handler(CommandHandler("help", self.help_command))
            self.app.add_handler(CommandHandler("whoami", self.whoami_command))
            self.app.add_handler(CommandHandler("myinfo", self.whoami_command))
            self.app.add_handler(CommandHandler("miniapp", self.miniapp_command))
            self.app.add_handler(CommandHandler("link", self.link_command))
            self.app.add_handler(CommandHandler("unlink", self.unlink_command))
            self.app.add_handler(CommandHandler("send", self.send_command))
            self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

            if settings.TELEGRAM_WEBHOOK_URL and "https://" in settings.TELEGRAM_WEBHOOK_URL:
                await self.setup_webhook()
            else:
                logger.info("Starting bot polling mode (development mode)")
                await self.start_polling()

            self.enabled = True
            logger.info("Telegram bot initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")

    async def setup_webhook(self):
        """Setup webhook for Telegram bot"""
        try:
            webhook_url = f"{settings.TELEGRAM_WEBHOOK_URL}/api/telegram/webhook"
            await self.app.bot.set_webhook(
                url=webhook_url,
                allowed_updates=["message", "callback_query", "web_app_data"],
            )
            logger.info(f"Webhook set to: {webhook_url}")
        except Exception as e:
            logger.error(f"Failed to setup webhook: {e}")

    async def get_user_info(self, telegram_chat_id: str) -> Optional[dict]:
        """Get platform user info by telegram_chat_id"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.telegram_chat_id == str(telegram_chat_id))
                )
                user = result.scalar_one_or_none()
                if user:
                    return {
                        "name": user.full_name,
                        "role": user.role,
                        "email": user.email,
                        "department": user.department,
                    }
        except Exception as e:
            logger.error(f"Error fetching user info: {e}")
        return None

    async def get_user_header(self, telegram_chat_id: str) -> str:
        """Get user info header for display"""
        user_info = await self.get_user_info(telegram_chat_id)
        if user_info:
            return (
                f"👤 <b>{user_info['name']}</b> "
                f"(<code>{user_info['role']}</code>)\n\n"
            )
        return ""

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = str(update.effective_user.id)
        user_header = await self.get_user_header(user_id)

        if user_header:
            message = (
                f"👋 <b>Xush kelibsiz!</b>\n\n"
                f"{user_header}"
                f"<b>🔗 Mavjud Buyruqlar:</b>\n"
                f"🎯 <code>/miniapp</code> - Mini App-ni ochish\n"
                f"📤 <code>/send &lt;xabar&gt;</code> - Xabar yuborish\n"
                f"❓ <code>/help</code> - Yordam olish\n"
                f"🔗 <code>/unlink</code> - Bog'lanishni o'chirish"
            )
        else:
            message = (
                "👋 <b>Xush kelibsiz AiPlatforma Telegram Bot-ga!</b>\n\n"
                "<b>🔗 BOSHLASH:</b>\n"
                "<code>/link</code> - Platform rolingiz bilan bog'lash\n\n"
                "<b>Boshqa Buyruqlar:</b>\n"
                "🎯 <code>/miniapp</code> - Mini App-ni ochish\n"
                "❓ <code>/help</code> - Yordam olish"
            )

        await update.message.reply_html(message)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        await update.message.reply_html(
            "<b>🤖 Telegram Bot Buyruqlari</b>\n\n"
            "<b>👤 SIZNING MA'LUMOTLAR:</b>\n"
            "<code>/whoami</code> - Profil ma'lumotlari\n"
            "<code>/myinfo</code> - To'liq ma'lumot\n\n"
            "<b>🔗 BOG'LANISH:</b>\n"
            "<code>/link</code> - Platform rolingiz bilan bog'lash\n"
            "<code>/unlink</code> - Bog'lanishni o'chirish\n\n"
            "<b>📱 BOSHQA:</b>\n"
            "<code>/start</code> - Bosh menyu\n"
            "<code>/miniapp</code> - Mini App-ni ochish\n"
            "<code>/send &lt;text&gt;</code> - Xabar yuborish\n\n"
            "<b>✨ Eslatma:</b>\n"
            "Bot sizning rolingiz bilan ishlaydi!"
        )

    async def miniapp_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /miniapp command"""
        miniapp_url = f"http://localhost:8000/telegram/miniapp"
        await update.message.reply_html(
            f"<b>🎯 Mini App</b>\n\n"
            f"<a href='{miniapp_url}'>📱 Mini App-ni ochish</a>\n\n"
            f"<b>yoki</b> URL-ni copy qiling:\n"
            f"<code>{miniapp_url}</code>"
        )

    async def link_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /link command - Link Telegram to platform account"""
        if not context.args:
            await update.message.reply_html(
                "<b>🔗 Telegram Hisobni Bog'lash</b>\n\n"
                "1️⃣ Platformada (http://localhost:8000) hisobingizga kiriting\n"
                "2️⃣ Settings → Integrations → Telegram → 'Подключить' bosing\n"
                "3️⃣ Token olib, quyidagi komandani yuboring:\n\n"
                "<code>/link &lt;token&gt;</code>\n\n"
                "✨ Bot avtomatik sizning rolni sync qiladi!"
            )
            return

        token = " ".join(context.args)
        user_id = str(update.effective_user.id)
        username = update.effective_user.username or "Unknown"

        async with AsyncSessionLocal() as db:
            success, message = await link_telegram_account(
                db=db,
                token=token,
                telegram_chat_id=user_id,
                telegram_username=username,
            )

            if success:
                await update.message.reply_html(f"<b>✅ Muvaffaqiyatli!</b>\n\n{message}")
                logger.info(f"Linked Telegram @{username} ({user_id}) to platform account")
            else:
                await update.message.reply_html(f"<b>❌ Xatolik</b>\n\n{message}")
                logger.warning(f"Failed to link Telegram @{username}: {message}")

    async def whoami_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /whoami or /myinfo command - Show user info"""
        user_id = str(update.effective_user.id)
        telegram_user = update.effective_user

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.telegram_chat_id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                await update.message.reply_html(
                    "❌ <b>Siz bog'lanmagansiz!</b>\n\n"
                    "Platform ma'lumotlarini ko'rish uchun avval bog'laning:\n\n"
                    "1️⃣ Platform-ga kiriting\n"
                    "2️⃣ Settings → Integrations → Telegram\n"
                    "3️⃣ 'Подключить' tugmasini bosing\n"
                    "4️⃣ Token olib quyidagini yuboring:\n"
                    "<code>/link &lt;token&gt;</code>"
                )
                return

            # Show detailed user info
            info_message = (
                f"✅ <b>SIZNING MA'LUMOTLARINGIZ</b>\n\n"
                f"👤 <b>Platform Profilи:</b>\n"
                f"  • Ism: <b>{user.full_name}</b>\n"
                f"  • Rol: <code>{user.role}</code>\n"
                f"  • Email: {user.email}\n"
                f"  • Telefon: {user.phone or 'Qo\'shilmagan'}\n"
                f"  • Departament: {user.department or 'Qo\'shilmagan'}\n\n"
                f"📱 <b>Telegram:</b>\n"
                f"  • Username: @{telegram_user.username or 'Yo\'q'}\n"
                f"  • Chat ID: <code>{user_id}</code>\n"
                f"  • Bog'lanish: ✅ Faol\n\n"
                f"🔧 <b>Buyruqlar:</b>\n"
                f"  • <code>/unlink</code> - Bog'lanishni o'chirish\n"
                f"  • <code>/help</code> - Yordam"
            )

            await update.message.reply_html(info_message)
            logger.info(f"User info requested: {user.email} ({user_id})")

    async def unlink_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unlink command - Remove Telegram link"""
        user_id = str(update.effective_user.id)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.telegram_chat_id == user_id)
            )
            user = result.scalar_one_or_none()

            if not user:
                await update.message.reply_html(
                    "❌ <b>Siz bog'lanmagansiz!</b>\n\n"
                    "Bog'lanish uchun:\n"
                    "<code>/link &lt;token&gt;</code>"
                )
                return

            # Unlink Telegram account
            user.telegram_chat_id = None
            await db.commit()

            await update.message.reply_html(
                f"✅ <b>Bog'lanish o'chirildi!</b>\n\n"
                f"👤 {user.full_name} ({user.role})\n\n"
                f"Qayta bog'lanish uchun Platform-dan token olib:\n"
                f"<code>/link &lt;token&gt;</code>"
            )
            logger.info(f"Unlinked Telegram {user_id} from user {user.email}")

    async def send_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /send command"""
        if not context.args:
            await update.message.reply_text("Xabar matni yuboring:\n/send <xabar>")
            return

        message = " ".join(context.args)
        await update.message.reply_text(f"✅ Xabar qabul qilindi:\n\n{message}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages"""
        user_id = update.effective_user.id
        message_text = update.message.text

        logger.info(f"Message from {user_id}: {message_text}")

        # Check if user is linked to platform
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(User.telegram_chat_id == str(user_id))
            )
            platform_user = result.scalar_one_or_none()

            if platform_user:
                response = (
                    f"✅ <b>Xabar qabul qilindi!</b>\n\n"
                    f"<b>👤 Sizning ma'lumotlaringiz:</b>\n"
                    f"Ism: {platform_user.full_name}\n"
                    f"Rol: {platform_user.role}\n"
                    f"Email: {platform_user.email}\n\n"
                    f"📝 <b>Xabar matni:</b>\n{message_text}"
                )
                await update.message.reply_html(response)
            else:
                await update.message.reply_html(
                    "❌ <b>Siz hali bog'lanmagansiz!</b>\n\n"
                    "Platformaga bog'lanish uchun:\n"
                    "<code>/link &lt;token&gt;</code> yuboring"
                )

    async def start_polling(self):
        """Start bot polling to receive updates"""
        if not self.app:
            return
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("Bot polling started successfully")
        except Exception as e:
            logger.error(f"Failed to start polling: {e}")

    async def stop_polling(self):
        """Stop bot polling"""
        if not self.app:
            return
        try:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            logger.info("Bot polling stopped")
        except Exception as e:
            logger.error(f"Error stopping polling: {e}")

    async def process_update(self, data: dict):
        """Process Telegram update from webhook"""
        if not self.app:
            return False
        try:
            update = Update.de_json(data, self.app.bot)
            if update:
                await self.app.process_update(update)
                return True
        except Exception as e:
            logger.error(f"Error processing update: {e}")
        return False


telegram_bot = TelegramBot()
