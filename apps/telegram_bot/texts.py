"""Telegram bot xabarlarining uz/ru/en tarjimalari.

Django i18n ishlatilmadi: bot alohida long-polling jarayonda ishlaydi va til
so'rov (request) emas, chat sozlamasidan (TelegramChat.language) olinadi.
"""

LANGS = ["uz", "ru", "en"]

T = {
    # --- Pastki menyu tugmalari -------------------------------------------
    "menu.profile": {"uz": "👤 Profil", "ru": "👤 Профиль", "en": "👤 Profile"},
    "menu.miniapp": {"uz": "🌐 Veb-ilova", "ru": "🌐 Веб-приложение", "en": "🌐 Web app"},
    "menu.upload": {"uz": "📎 Hujjat yuklash", "ru": "📎 Загрузить документ", "en": "📎 Upload document"},
    "menu.settings": {"uz": "⚙️ Sozlamalar", "ru": "⚙️ Настройки", "en": "⚙️ Settings"},
    "menu.help": {"uz": "ℹ️ Yordam", "ru": "ℹ️ Помощь", "en": "ℹ️ Help"},

    # --- Asosiy buyruqlar ---------------------------------------------------
    "start": {
        "uz": "\U0001F44B Salom! AiPlatforma botiga xush kelibsiz.\n"
              "/link &lt;token&gt; — hisobingizni ulash\n"
              "/whoami — profil ma'lumotlari\n"
              "/help — yordam",
        "ru": "\U0001F44B Здравствуйте! Добро пожаловать в бот AiPlatforma.\n"
              "/link &lt;token&gt; — привязать аккаунт\n"
              "/whoami — данные профиля\n"
              "/help — помощь",
        "en": "\U0001F44B Hello! Welcome to the AiPlatforma bot.\n"
              "/link &lt;token&gt; — link your account\n"
              "/whoami — profile info\n"
              "/help — help",
    },
    "help": {
        "uz": "/start — botni ishga tushirish\n"
              "/link &lt;token&gt; — hisobni ulash\n"
              "/unlink — hisobni uzish\n"
              "/whoami — profil ma'lumotlari\n"
              "/miniapp — veb-ilova havolasi\n\n"
              "📎 Admin/menejerlar fayl yuborib, izohida mazmunini yozsa, "
              "u platformadagi hujjatlar bo'limiga saqlanadi.",
        "ru": "/start — запустить бота\n"
              "/link &lt;token&gt; — привязать аккаунт\n"
              "/unlink — отвязать аккаунт\n"
              "/whoami — данные профиля\n"
              "/miniapp — ссылка на веб-приложение\n\n"
              "📎 Если админ/менеджер отправит файл с описанием в подписи, "
              "он сохранится в разделе документов платформы.",
        "en": "/start — start the bot\n"
              "/link &lt;token&gt; — link account\n"
              "/unlink — unlink account\n"
              "/whoami — profile info\n"
              "/miniapp — web app link\n\n"
              "📎 When an admin/manager sends a file with a caption describing it, "
              "it is saved to the platform's documents section.",
    },
    "not_linked": {
        "uz": "Hisobingiz hali ulanmagan. /link <token> dan foydalaning.",
        "ru": "Ваш аккаунт ещё не привязан. Используйте /link <token>.",
        "en": "Your account is not linked yet. Use /link <token>.",
    },
    "link.usage": {
        "uz": "Foydalanish: /link <token>",
        "ru": "Использование: /link <token>",
        "en": "Usage: /link <token>",
    },
    "link.success": {
        "uz": "✅ Hisobingiz muvaffaqiyatli ulandi!\n\n"
              "👤 <b>{name}</b>\n🎖 Rol: <b>{role}</b>\n📧 {email}\n\n"
              "Endi platforma bildirishnomalari (vazifalar, muddatlar, "
              "tasdiqlashlar) shu yerga keladi.",
        "ru": "✅ Аккаунт успешно привязан!\n\n"
              "👤 <b>{name}</b>\n🎖 Роль: <b>{role}</b>\n📧 {email}\n\n"
              "Теперь уведомления платформы (задачи, сроки, согласования) "
              "будут приходить сюда.",
        "en": "✅ Account linked successfully!\n\n"
              "👤 <b>{name}</b>\n🎖 Role: <b>{role}</b>\n📧 {email}\n\n"
              "Platform notifications (tasks, deadlines, approvals) "
              "will now arrive here.",
    },
    "link.invalid": {
        "uz": "Token yaroqsiz yoki muddati o'tgan.",
        "ru": "Токен недействителен или просрочен.",
        "en": "The token is invalid or expired.",
    },
    "unlinked": {
        "uz": "Hisobingiz uzildi.",
        "ru": "Аккаунт отвязан.",
        "en": "Your account has been unlinked.",
    },

    # --- Fayl yuklash -------------------------------------------------------
    "upload.hint": {
        "uz": "📎 Faylni shu chatga yuboring va izohida (caption) hujjat "
              "mazmunini yozing — u hujjat nomi sifatida saqlanadi.\n"
              "Keyin qaysi loyihaga saqlashni tanlaysiz.\n\n"
              "Eslatma: fayl yuklash admin va menejerlar uchun, hajmi 20 MB gacha.",
        "ru": "📎 Отправьте файл в этот чат и в подписи (caption) опишите "
              "содержание документа — это станет его названием.\n"
              "Затем выберите проект для сохранения.\n\n"
              "Примечание: загрузка доступна админам и менеджерам, до 20 МБ.",
        "en": "📎 Send a file to this chat with a caption describing the "
              "document — the caption becomes its name.\n"
              "Then choose which project to save it to.\n\n"
              "Note: uploads are for admins and managers, up to 20 MB.",
    },
    "upload.admins_only": {
        "uz": "Fayl yuklash faqat admin va menejerlar uchun.",
        "ru": "Загрузка файлов доступна только админам и менеджерам.",
        "en": "File uploads are for admins and managers only.",
    },
    "upload.no_projects": {
        "uz": "Platformada hali loyihalar yo'q — avval loyiha yarating.",
        "ru": "На платформе пока нет проектов — сначала создайте проект.",
        "en": "There are no projects on the platform yet — create one first.",
    },
    "upload.caption_required": {
        "uz": "Fayl bilan birga izohda (caption) hujjat mazmunini yozing — "
              "u hujjat nomi sifatida saqlanadi. Faylni izoh bilan qayta yuboring.",
        "ru": "Вместе с файлом в подписи (caption) опишите содержание документа — "
              "это станет его названием. Отправьте файл ещё раз с подписью.",
        "en": "Add a caption describing the document — it becomes the document "
              "name. Please resend the file with a caption.",
    },
    "upload.too_big": {
        "uz": "Fayl 20 MB dan katta — Telegram bot orqali yuklab bo'lmaydi. "
              "Katta fayllarni sayt orqali yuklang.",
        "ru": "Файл больше 20 МБ — через Telegram-бота загрузить нельзя. "
              "Большие файлы загружайте через сайт.",
        "en": "The file is over 20 MB — it can't be uploaded via the Telegram "
              "bot. Upload large files through the website.",
    },
    "upload.choose_project": {
        "uz": "📄 <b>{caption}</b>\nQaysi loyihaga saqlansin?",
        "ru": "📄 <b>{caption}</b>\nВ какой проект сохранить?",
        "en": "📄 <b>{caption}</b>\nWhich project should it be saved to?",
    },
    "upload.cancel": {
        "uz": "❌ Bekor qilish",
        "ru": "❌ Отмена",
        "en": "❌ Cancel",
    },
    "upload.cancelled": {
        "uz": "Bekor qilindi.",
        "ru": "Отменено.",
        "en": "Cancelled.",
    },
    "upload.expired": {
        "uz": "Bu so'rov eskirgan — faylni izoh bilan qayta yuboring.",
        "ru": "Этот запрос устарел — отправьте файл с подписью заново.",
        "en": "This request has expired — resend the file with a caption.",
    },
    "upload.downloading": {
        "uz": "⏳ Fayl yuklanmoqda...",
        "ru": "⏳ Файл загружается...",
        "en": "⏳ Downloading the file...",
    },
    "upload.download_error": {
        "uz": "Faylni Telegramdan yuklab olishda xatolik. Qayta urinib ko'ring.",
        "ru": "Ошибка при получении файла из Telegram. Попробуйте ещё раз.",
        "en": "Failed to download the file from Telegram. Please try again.",
    },
    "upload.save_error": {
        "uz": "Saqlashda xatolik: loyiha yoki hisob topilmadi.",
        "ru": "Ошибка сохранения: проект или аккаунт не найден.",
        "en": "Save failed: project or account not found.",
    },
    "upload.saved": {
        "uz": "✅ Hujjat saqlandi: <b>{name}</b>\n📁 Loyiha: {project}\n🔗 {url}",
        "ru": "✅ Документ сохранён: <b>{name}</b>\n📁 Проект: {project}\n🔗 {url}",
        "en": "✅ Document saved: <b>{name}</b>\n📁 Project: {project}\n🔗 {url}",
    },

    # --- AI chat --------------------------------------------------------------
    "ai.error": {
        "uz": "Kechirasiz, javob tayyorlashda xatolik yuz berdi. "
              "Birozdan keyin qayta urinib ko'ring.",
        "ru": "Извините, при подготовке ответа произошла ошибка. "
              "Попробуйте немного позже.",
        "en": "Sorry, something went wrong while preparing a reply. "
              "Please try again shortly.",
    },
    "ai.not_linked": {
        "uz": "Hisobingiz hali ulanmagan. Saytdagi profil sahifasida "
              "Telegram → Ulash tugmasini bosing yoki /link <token> yuboring.",
        "ru": "Ваш аккаунт ещё не привязан. На странице профиля сайта нажмите "
              "Telegram → Привязать или отправьте /link <token>.",
        "en": "Your account is not linked yet. On your profile page press "
              "Telegram → Link, or send /link <token>.",
    },
    "ai.not_configured": {
        "uz": "AI yordamchi hozircha sozlanmagan.",
        "ru": "AI-помощник пока не настроен.",
        "en": "The AI assistant is not configured yet.",
    },

    # --- Sozlamalar -------------------------------------------------------------
    "settings.title": {
        "uz": "⚙️ Sozlamalar",
        "ru": "⚙️ Настройки",
        "en": "⚙️ Settings",
    },
    "settings.language_btn": {
        "uz": "🌐 Til tanlash",
        "ru": "🌐 Выбрать язык",
        "en": "🌐 Choose language",
    },
    "settings.choose_language": {
        "uz": "Tilni tanlang:",
        "ru": "Выберите язык:",
        "en": "Choose a language:",
    },
    "settings.language_saved": {
        "uz": "✅ Til o'zgartirildi: Oʻzbekcha",
        "ru": "✅ Язык изменён: Русский",
        "en": "✅ Language changed: English",
    },
}

MENU_KEYS = ["menu.profile", "menu.miniapp", "menu.upload", "menu.settings", "menu.help"]

LANGUAGE_LABELS = {"uz": "🇺🇿 Oʻzbekcha", "ru": "🇷🇺 Русский", "en": "🇬🇧 English"}


def t(key, lang="uz", **fmt):
    entry = T[key]
    text = entry.get(lang) or entry["uz"]
    return text.format(**fmt) if fmt else text


def menu_key_for(text):
    """Tugma matnidan (istalgan tilda) menyu kalitini topadi."""
    for key in MENU_KEYS:
        if text in T[key].values():
            return key
    return None


def all_menu_labels():
    """Barcha tillardagi menyu tugmalari matnlari (MessageHandler filtri uchun)."""
    return [T[key][lang] for key in MENU_KEYS for lang in LANGS]
