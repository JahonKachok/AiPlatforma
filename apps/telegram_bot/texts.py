"""Telegram bot xabarlarining uz/ru/en tarjimalari.

Django i18n ishlatilmadi: bot alohida long-polling jarayonda ishlaydi va til
so'rov (request) emas, chat sozlamasidan (TelegramChat.language) olinadi.
"""

LANGS = ["uz", "ru", "en"]

T = {
    # --- Pastki menyu tugmalari -------------------------------------------
    "menu.profile": {"uz": "👤 Profil", "ru": "👤 Профиль", "en": "👤 Profile"},
    "menu.upload": {"uz": "📎 Hujjat yuklash", "ru": "📎 Загрузить документ", "en": "📎 Upload document"},
    "menu.settings": {"uz": "⚙️ Sozlamalar", "ru": "⚙️ Настройки", "en": "⚙️ Settings"},
    "menu.help": {"uz": "ℹ️ Yordam", "ru": "ℹ️ Помощь", "en": "ℹ️ Help"},
    "menu.report": {"uz": "📊 AI hisobot", "ru": "📊 AI-отчёт", "en": "📊 AI report"},

    # --- Asosiy buyruqlar ---------------------------------------------------
    "start": {
        "uz": "\U0001F44B Salom! Men <b>BuildFlow</b> botiman — qurilishni "
              "avtomatlashtirish platformasining rasmiy yordamchisi.\n\n"
              "Nimalar qila olaman:\n"
              "🔔 Vazifalar, muddatlar va tasdiqlashlar haqida bildirishnoma yuboraman\n"
              "🤖 Loyihalar va vazifalar bo'yicha AI yordamida javob beraman — "
              "oddiy xabar yozing (🎤 ovozli xabar ham bo'ladi)\n"
              "📎 Hujjatlarni to'g'ridan-to'g'ri platformaga yuklayman (admin/menejerlar)\n"
              "📊 Rahbarlar uchun AI muddat-hisobotini tayyorlayman\n\n"
              "Boshlash uchun hisobingizni ulang: saytdagi profil sahifasida "
              "<b>Telegram → Ulash</b> tugmasini bosing yoki /link &lt;token&gt; "
              "yuboring. To'liq yordam — /help\n\n"
              "🌐 Interfeys tilini tanlang:",
        "ru": "\U0001F44B Здравствуйте! Я бот <b>BuildFlow</b> — официальный "
              "помощник платформы автоматизации строительства.\n\n"
              "Что я умею:\n"
              "🔔 Присылаю уведомления о задачах, сроках и согласованиях\n"
              "🤖 Отвечаю на вопросы по проектам и задачам с помощью AI — "
              "просто напишите сообщение (🎤 можно и голосом)\n"
              "📎 Загружаю документы прямо на платформу (для админов/менеджеров)\n"
              "📊 Готовлю AI-отчёт по срокам для руководителей\n\n"
              "Чтобы начать, привяжите аккаунт: в профиле на сайте нажмите "
              "<b>Telegram → Привязать</b> или отправьте /link &lt;token&gt;. "
              "Полная справка — /help\n\n"
              "🌐 Выберите язык интерфейса:",
        "en": "\U0001F44B Hello! I'm the <b>BuildFlow</b> bot — the official "
              "assistant of the Construction Automation Platform.\n\n"
              "What I can do:\n"
              "🔔 Send notifications about tasks, deadlines and approvals\n"
              "🤖 Answer questions about projects and tasks with AI — "
              "just type a message (🎤 voice messages work too)\n"
              "📎 Upload documents straight to the platform (admins/managers)\n"
              "📊 Prepare an AI deadline report for managers\n\n"
              "To get started, link your account: on your profile page press "
              "<b>Telegram → Link</b>, or send /link &lt;token&gt;. "
              "Full help — /help\n\n"
              "🌐 Choose your interface language:",
    },
    "help": {
        "uz": "/start — botni ishga tushirish\n"
              "/link &lt;token&gt; — hisobni ulash\n"
              "/unlink — hisobni uzish\n"
              "/whoami — profil ma'lumotlari\n\n"
              "📎 Admin/menejerlar fayl yuborib, izohida mazmunini yozsa, "
              "u platformadagi hujjatlar bo'limiga saqlanadi.\n\n"
              "🤖 AI yordamchi: oddiy xabar yozing — loyihalar va vazifalar "
              "bo'yicha javob beradi. Admin/menejerlar buyruq ham bera oladi:\n"
              "• «Ofis binosi loyihasini yarat, muddati 2026-12-31»\n"
              "• «Sardorga chizmalarni tekshirish vazifasini ber»\n"
              "• «Chizmalar vazifasini yakunlanganga o'tkaz»\n"
              "• «Shartnoma degan hujjatni top»\n"
              "🎤 Ovozli xabar ham yuborsangiz bo'ladi (3 daqiqagacha).",
        "ru": "/start — запустить бота\n"
              "/link &lt;token&gt; — привязать аккаунт\n"
              "/unlink — отвязать аккаунт\n"
              "/whoami — данные профиля\n\n"
              "📎 Если админ/менеджер отправит файл с описанием в подписи, "
              "он сохранится в разделе документов платформы.\n\n"
              "🤖 AI-помощник: напишите обычное сообщение — ответит по проектам "
              "и задачам. Админы/менеджеры могут давать команды:\n"
              "• «Создай проект Офисное здание со сроком 2026-12-31»\n"
              "• «Поручи Сардору проверку чертежей»\n"
              "• «Переведи задачу по чертежам в завершённые»\n"
              "• «Найди документ со словом договор»\n"
              "🎤 Можно отправлять и голосовые сообщения (до 3 минут).",
        "en": "/start — start the bot\n"
              "/link &lt;token&gt; — link account\n"
              "/unlink — unlink account\n"
              "/whoami — profile info\n\n"
              "📎 When an admin/manager sends a file with a caption describing it, "
              "it is saved to the platform's documents section.\n\n"
              "🤖 AI assistant: just type a message — it answers about projects "
              "and tasks. Admins/managers can also give commands:\n"
              "• \"Create the Office Building project due 2026-12-31\"\n"
              "• \"Assign drawing review to Sardor\"\n"
              "• \"Mark the drawings task as completed\"\n"
              "• \"Find the contract document\"\n"
              "🎤 You can also send voice messages (up to 3 minutes).",
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
    "report.generating": {
        "uz": "⏳ Hisobot tayyorlanmoqda...",
        "ru": "⏳ Отчёт готовится...",
        "en": "⏳ Preparing the report...",
    },
    "report.empty": {
        "uz": "✅ Muddati o'tgan yoki yaqin muddatli ochiq vazifalar yo'q — hammasi nazoratda.",
        "ru": "✅ Просроченных или срочных открытых задач нет — всё под контролем.",
        "en": "✅ No overdue or due-soon open tasks — everything is under control.",
    },
    "report.admins_only": {
        "uz": "AI hisobot faqat admin va menejerlar uchun.",
        "ru": "AI-отчёт доступен только админам и менеджерам.",
        "en": "The AI report is for admins and managers only.",
    },
    "voice.too_long": {
        "uz": "Ovozli xabar 3 daqiqadan oshmasligi kerak. Qisqaroq qilib "
              "qayta yuboring.",
        "ru": "Голосовое сообщение не должно быть длиннее 3 минут. "
              "Отправьте покороче.",
        "en": "Voice messages must be under 3 minutes. Please send a "
              "shorter one.",
    },
    "ai.rate_limited": {
        "uz": "So'rovlar juda tez-tez yuborilmoqda. Bir necha daqiqadan "
              "keyin qayta urinib ko'ring.",
        "ru": "Слишком много запросов подряд. Попробуйте снова через "
              "несколько минут.",
        "en": "Too many requests in a short time. Please try again in a "
              "few minutes.",
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

MENU_KEYS = ["menu.profile", "menu.upload", "menu.settings", "menu.help", "menu.report"]

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
