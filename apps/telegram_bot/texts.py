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
        "uz": "\U0001F44B Salom! Men <b>GASTEC</b> botiman — qurilishni "
              "avtomatlashtirish platformasining rasmiy yordamchisi.\n\n"
              "Nimalar qila olaman:\n"
              "🔔 Vazifalar, muddatlar va tasdiqlashlar haqida bildirishnoma yuboraman\n"
              "🤖 Loyihalar va vazifalar bo'yicha AI yordamida javob beraman — "
              "oddiy xabar yozing (🎤 ovozli xabar ham bo'ladi)\n"
              "📎 Hujjatlarni to'g'ridan-to'g'ri platformaga yuklayman\n"
              "📊 Rahbarlar uchun AI muddat-hisobotini tayyorlayman\n\n"
              "Boshlash uchun hisobingizni ulang: saytdagi profil sahifasida "
              "<b>Telegram → Ulash</b> tugmasini bosing yoki /link &lt;token&gt; "
              "yuboring. To'liq yordam — /help\n\n"
              "🌐 Interfeys tilini tanlang:",
        "ru": "\U0001F44B Здравствуйте! Я бот <b>GASTEC</b> — официальный "
              "помощник платформы автоматизации строительства.\n\n"
              "Что я умею:\n"
              "🔔 Присылаю уведомления о задачах, сроках и согласованиях\n"
              "🤖 Отвечаю на вопросы по проектам и задачам с помощью AI — "
              "просто напишите сообщение (🎤 можно и голосом)\n"
              "📎 Загружаю документы прямо на платформу\n"
              "📊 Готовлю AI-отчёт по срокам для руководителей\n\n"
              "Чтобы начать, привяжите аккаунт: в профиле на сайте нажмите "
              "<b>Telegram → Привязать</b> или отправьте /link &lt;token&gt;. "
              "Полная справка — /help\n\n"
              "🌐 Выберите язык интерфейса:",
        "en": "\U0001F44B Hello! I'm the <b>GASTEC</b> bot — the official "
              "assistant of the Construction Automation Platform.\n\n"
              "What I can do:\n"
              "🔔 Send notifications about tasks, deadlines and approvals\n"
              "🤖 Answer questions about projects and tasks with AI — "
              "just type a message (🎤 voice messages work too)\n"
              "📎 Upload documents straight to the platform\n"
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
              "📎 Fayl yuborib, izohida mazmunini yozsangiz, "
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
              "📎 Если вы отправите файл с описанием в подписи, "
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
              "📎 When you send a file with a caption describing it, "
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
              "Eslatma: fayl hajmi 20 MB gacha bo'lishi kerak.",
        "ru": "📎 Отправьте файл в этот чат и в подписи (caption) опишите "
              "содержание документа — это станет его названием.\n"
              "Затем выберите проект для сохранения.\n\n"
              "Примечание: размер файла — до 20 МБ.",
        "en": "📎 Send a file to this chat with a caption describing the "
              "document — the caption becomes its name.\n"
              "Then choose which project to save it to.\n\n"
              "Note: file size must be under 20 MB.",
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
    "upload.bad_type": {
        "uz": "Bu turdagi faylni yuklab bo'lmaydi. Ruxsat etilgan turlar: {allowed}.",
        "ru": "Файлы такого типа загружать нельзя. Разрешённые типы: {allowed}.",
        "en": "Files of this type can't be uploaded. Allowed types: {allowed}.",
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

    # --- Pult dispetcheri (apps/pult/dispatcher.py) -------------------------
    "pd.accept": {"uz": "✅ Qabul qilaman", "ru": "✅ Принять", "en": "✅ Accept"},
    "pd.accept_days": {"uz": "✅ Qabul ({days} kun)", "ru": "✅ Принять ({days} дн.)", "en": "✅ Accept ({days} d)"},
    "pd.own_days": {"uz": "{days} kun", "ru": "{days} дн.", "en": "{days} d"},
    "pd.decline": {"uz": "❌ Rad etish", "ru": "❌ Отказ", "en": "❌ Decline"},
    "pd.submit": {"uz": "📤 Tekshiruvga topshirish", "ru": "📤 Сдать на проверку", "en": "📤 Submit for review"},
    "pd.later": {"uz": "Keyinroq", "ru": "Позже", "en": "Later"},
    # --- Orchestrator agentlari (apps/ai_agents/orchestrator.py) ----------
    "ag.confirm": {"uz": "✅ Yozish", "ru": "✅ Записать", "en": "✅ Save"},
    "ag.cancel": {"uz": "❌ Bekor", "ru": "❌ Отмена", "en": "❌ Cancel"},
    "ag.cancelled": {"uz": "Bekor qilindi.", "ru": "Отменено.", "en": "Cancelled."},
    "ag.project_summary": {
        "uz": "💰 Kaznachey: {sign}{money}\nLoyiha: {project}\nKim: {who}\nToifa: {cat}\nSana: {date}\nYozaymi?",
        "ru": "💰 Казначей: {sign}{money}\nПроект: {project}\nКто: {who}\nКатегория: {cat}\nДата: {date}\nЗаписать?",
        "en": "💰 Treasurer: {sign}{money}\nProject: {project}\nWho: {who}\nCategory: {cat}\nDate: {date}\nSave it?",
    },
    "ag.office_summary": {
        "uz": "🏢 Zavxoz: ofis xarajati {money}\nToifa: {cat}\nKim: {who}\nSana: {date}\nIzoh: {note}\nYozaymi?",
        "ru": "🏢 Завхоз: офисный расход {money}\nКатегория: {cat}\nКому: {who}\nДата: {date}\nПримечание: {note}\nЗаписать?",
        "en": "🏢 Quartermaster: office cost {money}\nCategory: {cat}\nTo: {who}\nDate: {date}\nNote: {note}\nSave it?",
    },
    "ag.project_saved": {
        "uz": "✅ Operatsiya №{n} yozildi. «{project}» balansi: {balance}",
        "ru": "✅ Операция №{n} записана. Баланс «{project}»: {balance}",
        "en": "✅ Operation #{n} saved. «{project}» balance: {balance}",
    },
    "ag.office_saved": {
        "uz": "✅ Ofis xarajati yozildi: {money} ({cat}).",
        "ru": "✅ Офисный расход записан: {money} ({cat}).",
        "en": "✅ Office cost saved: {money} ({cat}).",
    },
    "ag.project_unknown": {
        "uz": "Loyiha aniqlanmadi («{name}»). Loyiha nomini aniqroq yozing.",
        "ru": "Не понял проект («{name}»). Напишите название проекта точнее.",
        "en": "Could not find the project («{name}»). Please name it more exactly.",
    },
    "ag.finance_denied": {
        "uz": "Moliya yozuvlarini faqat rahbar yoki buxgalter kiritadi.",
        "ru": "Финансовые записи вносят только руководитель или бухгалтер.",
        "en": "Only a manager or accountant can record money operations.",
    },
    "ag.not_understood": {
        "uz": "Tushuna olmadim — summani, valyutani va loyihani aniq yozing.",
        "ru": "Не понял — напишите сумму, валюту и проект точнее.",
        "en": "I did not get it — please state the amount, currency and project.",
    },
    "ag.remembered": {
        "uz": "🧠 Eslab qoldim — keyingi vazifalarda shunday qilaman.",
        "ru": "🧠 Запомнил — буду так делать в следующих задачах.",
        "en": "🧠 Noted — I will apply this from now on.",
    },
    "ag.no_files": {"uz": "Mos fayl topilmadi.", "ru": "Подходящих файлов нет.", "en": "No matching files."},
    "ag.recipient_unknown": {
        "uz": "Qabul qiluvchi aniq emas: «{name}».",
        "ru": "Не понял получателя: «{name}».",
        "en": "Recipient is unclear: «{name}».",
    },
    "ag.recipient_no_tg": {
        "uz": "{name} Telegram'ni platformaga ulamagan.",
        "ru": "{name} не привязал Telegram к платформе.",
        "en": "{name} has not linked Telegram.",
    },
    "ag.files_sending": {
        "uz": "📦 Arxivarius: {count} ta fayl {name} ga yuborilmoqda.",
        "ru": "📦 Архивариус: {count} файл(ов) отправляются — {name}.",
        "en": "📦 Archivist: sending {count} file(s) to {name}.",
    },
    "ag.jobs_queued": {
        "uz": "🖥 {count} ta fayl ishchi kompyuter navbatiga qo'yildi — tayyor bo'lgach shu yerga yuboraman.",
        "ru": "🖥 Файлов в очереди рабочего компьютера: {count} — пришлю сюда, когда будет готово.",
        "en": "🖥 {count} file(s) queued on the worker PC — I will send them here when ready.",
    },
    "ag.jobs_queued_offline": {
        "uz": "🖥 {count} ta fayl navbatga qo'yildi, lekin ishchi kompyuter hozir o'chiq — yoqilgach bajariladi.",
        "ru": "🖥 Файлов в очереди: {count}, но рабочий компьютер сейчас выключен — выполнится, когда включится.",
        "en": "🖥 {count} file(s) queued, but the worker PC is offline — they run once it is back.",
    },
    "ag.which_lang": {
        "uz": "Qaysi tilga tarjima qilay: xitoy, rus yoki ingliz?",
        "ru": "На какой язык перевести: китайский, русский или английский?",
        "en": "Translate into which language: Chinese, Russian or English?",
    },
    "ag.letter_queued": {
        "uz": "✍️ «{title}» tayyorlandi, PDF qilinmoqda — keyin direktorga imzoga yuboraman.",
        "ru": "✍️ «{title}» подготовлено, делаю PDF — затем отправлю директору на подпись.",
        "en": "✍️ «{title}» is drafted, making the PDF — then it goes to the director for signature.",
    },
    "ag.letter_queued_offline": {
        "uz": "✍️ «{title}» tayyorlandi. PDF ishchi kompyuter yoqilgach qilinadi va direktorga imzoga ketadi.",
        "ru": "✍️ «{title}» подготовлено. PDF сделает рабочий компьютер, когда включится, и отправит директору.",
        "en": "✍️ «{title}» is drafted. The worker PC will make the PDF when it is back and send it for signature.",
    },
    "ag.sign_ok": {"uz": "✅ Imzo va muhr", "ru": "✅ Подписать и печать", "en": "✅ Sign and seal"},
    "ag.sign_no": {"uz": "❌ Rad etish", "ru": "❌ Отклонить", "en": "❌ Reject"},
    "ag.sign_ask": {"uz": "Imzoga: {name} ({who})", "ru": "На подпись: {name} ({who})", "en": "For signature: {name} ({who})"},
    "ag.sign_question": {
        "uz": "«{name}» ga imzo va muhr qo'yaymi?",
        "ru": "Поставить подпись и печать на «{name}»?",
        "en": "Put the signature and seal on «{name}»?",
    },
    "ag.sign_sent": {
        "uz": "📨 Hujjat direktorga imzoga yuborildi.",
        "ru": "📨 Документ отправлен директору на подпись.",
        "en": "📨 Sent to the director for signature.",
    },
    "ag.sign_pdf_only": {
        "uz": "Imzoga faqat PDF yuboring.",
        "ru": "На подпись отправляйте PDF.",
        "en": "Send a PDF for signature.",
    },
    "ag.no_signers": {
        "uz": "Imzo huquqi bor va Telegram'i ulangan rahbar topilmadi.",
        "ru": "Нет руководителя с правом подписи и привязанным Telegram.",
        "en": "No signer with a linked Telegram was found.",
    },
    "ag.sign_denied": {
        "uz": "Imzo va muhrni faqat direktor (imzo huquqi borlar) qo'yadi.",
        "ru": "Подпись и печать ставит только директор (с правом подписи).",
        "en": "Only the director (signers) can sign and seal.",
    },
    "ag.sign_rejected": {"uz": "Rad etildi, muallifga xabar berildi.", "ru": "Отклонено, автору сообщено.", "en": "Rejected, the author was told."},
    "ag.no_seal": {
        "uz": "Imzo va muhr rasmlari yuklanmagan (Pult → Запросы → Подпись и печать).",
        "ru": "Не загружены подпись и печать (Пульт → Запросы → Подпись и печать).",
        "en": "Signature and seal images are not uploaded (Pult → Requests).",
    },
    "ag.no_label": {
        "uz": "PDF'da «Директор» yozuvi topilmadi (skan bo'lsa matn qatlami yo'q). Saytdagi Pult orqali qo'lda qo'ying.",
        "ru": "В PDF не найдено слово «Директор» (у скана нет текста). Поставьте вручную через Пульт на сайте.",
        "en": "No «Директор» label found in the PDF (scans have no text layer). Place it manually in the Pult.",
    },
    "ag.signed": {"uz": "✅ «{name}» imzolandi va muhrlandi.", "ru": "✅ «{name}» подписан и заверен печатью.", "en": "✅ «{name}» signed and sealed."},
    "ag.voice_needs_gemini": {
        "uz": "Ovozli xabarni tushunish uchun admin panelda Gemini kaliti kerak. Hozircha matn bilan yozing.",
        "ru": "Для голосовых сообщений нужен ключ Gemini в админ-панели. Пока напишите текстом.",
        "en": "Voice messages need a Gemini key in the admin panel. Please type for now.",
    },
    "pd.no_active": {
        "uz": "Hozir ishdagi vazifangiz yo'q.",
        "ru": "Сейчас у вас нет задач в работе.",
        "en": "You have no tasks in progress.",
    },
    "pd.choose_days": {
        "uz": "Muddat belgilanmagan — necha kunda bajarasiz? ГИП tasdiqlaydi.",
        "ru": "Срок не назван — за сколько дней сделаете? ГИП утвердит.",
        "en": "No term set — how many days do you need? The GIP will approve.",
    },
    "pd.ask_decline": {
        "uz": "№{n}: rad etish sababini yozing (ТЗ'dagi kamchilik):",
        "ru": "№{n}: напишите причину отказа (что не так в ТЗ):",
        "en": "#{n}: write why you decline (what is wrong in the brief):",
    },
    "pd.done": {"uz": "✅ №{n}: {status}", "ru": "✅ №{n}: {status}", "en": "✅ #{n}: {status}"},
    "pd.report_saved": {
        "uz": "✅ №{n}: bugungi hisobot — {pct}%",
        "ru": "✅ №{n}: отчёт за сегодня — {pct}%",
        "en": "✅ #{n}: today's report — {pct}%",
    },
    "pd.ask_mid_file": {
        "uz": "№{n} 50% ga yetdi. Oraliq faylni (isxodnik) shu chatga yuboring — u platformaga va Google Drive'ga yuklanadi.",
        "ru": "№{n} достигла 50%. Пришлите сюда промежуточный файл (исходник) — он попадёт на платформу и в Google Drive.",
        "en": "#{n} reached 50%. Send the intermediate (source) file here — it goes to the platform and Google Drive.",
    },
    "pd.mid_saved": {
        "uz": "📎 №{n}: oraliq fayl qabul qilindi — {name}",
        "ru": "📎 №{n}: промежуточный файл принят — {name}",
        "en": "📎 #{n}: intermediate file received — {name}",
    },
    "pd.mid_later": {
        "uz": "Mayli. Faylni keyin ham yuborishingiz mumkin — 50% dan oshgan vazifa bo'yicha bot yana so'raydi.",
        "ru": "Хорошо. Файл можно прислать позже — бот напомнит по задаче выше 50%.",
        "en": "OK. You can send the file later — the bot will remind you.",
    },
    "pd.report_ask": {
        "uz": "📊 №{n} «{title}» — bugun necha foiz bajarildi? (hozir {pct}%)",
        "ru": "📊 №{n} «{title}» — сколько процентов сделано сегодня? (сейчас {pct}%)",
        "en": "📊 #{n} «{title}» — how much is done today? (now {pct}%)",
    },
    "pd.alarm_50": {
        "uz": "🚨 TREVOGA №{n} «{title}»: muddatning {elapsed}% o'tdi, bajarilgani {pct}% (50% ga yetmagan). Muddat: {plan}.",
        "ru": "🚨 ТРЕВОГА №{n} «{title}»: прошло {elapsed}% срока, сделано {pct}% (меньше 50%). Срок: {plan}.",
        "en": "🚨 ALARM #{n} «{title}»: {elapsed}% of the term passed, {pct}% done (below 50%). Due: {plan}.",
    },
    "pd.alarm_70": {
        "uz": "🚨 TREVOGA №{n} «{title}»: muddatning {elapsed}% o'tdi, bajarilgani {pct}% (70% ga yetmagan). Muddat: {plan}.",
        "ru": "🚨 ТРЕВОГА №{n} «{title}»: прошло {elapsed}% срока, сделано {pct}% (меньше 70%). Срок: {plan}.",
        "en": "🚨 ALARM #{n} «{title}»: {elapsed}% of the term passed, {pct}% done (below 70%). Due: {plan}.",
    },
    "pd.not_linked": {
        "uz": "Telegram hisobingiz platformaga ulanmagan.",
        "ru": "Ваш Telegram не привязан к платформе.",
        "en": "Your Telegram is not linked to the platform.",
    },
    "pd.expired": {
        "uz": "Bu tugma eskirgan. Vazifani platformada oching.",
        "ru": "Кнопка устарела. Откройте задачу на платформе.",
        "en": "This button is outdated. Open the task on the platform.",
    },
    "pd.file_bad": {
        "uz": "Bu fayl turi qabul qilinmaydi yoki fayl juda katta (20 MB gacha).",
        "ru": "Такой тип файла не принимается или файл слишком большой (до 20 МБ).",
        "en": "This file type is not accepted or the file is too large (up to 20 MB).",
    },
    "pd.kpi": {
        "uz": "📈 <b>KPI — {month}</b>\nBallaringiz: <b>{points}</b> (qabul qilingan vazifalar: {tasks})\nReytingdagi o'rin: {rank} / {total}",
        "ru": "📈 <b>KPI — {month}</b>\nВаши баллы: <b>{points}</b> (принято задач: {tasks})\nМесто в рейтинге: {rank} / {total}",
        "en": "📈 <b>KPI — {month}</b>\nYour points: <b>{points}</b> (accepted tasks: {tasks})\nRank: {rank} / {total}",
    },
    "pd.kpi_rules": {
        "uz": "⚖️ <b>KPI qoidalari</b> — ballar avtomatik yoziladi va iltimos bilan o'zgartirilmaydi:\n"
              "• muddatdan oldin topshirish: {early}\n• o'z vaqtida: {ontime}\n• kechikish ({late_days} kundan ko'p): {late}\n"
              "• qayta ishlashsiz qabul: {clean}; har bir qayta ishlash: −{rework}\n"
              "• o'tkazib yuborilgan kunlik hisobot: −{missed} (vazifa uchun ko'pi bilan −{missed_max})",
        "ru": "⚖️ <b>Правила KPI</b> — баллы начисляются автоматически и по просьбам не меняются:\n"
              "• сдача раньше срока: {early}\n• вовремя: {ontime}\n• опоздание (больше {late_days} дн.): {late}\n"
              "• принято без доработок: {clean}; каждая доработка: −{rework}\n"
              "• пропуск ежедневного отчёта: −{missed} (не больше −{missed_max} за задачу)",
        "en": "⚖️ <b>KPI rules</b> — points are applied automatically and are not changed on request:\n"
              "• submitted early: {early}\n• on time: {ontime}\n• late (more than {late_days} d): {late}\n"
              "• accepted without reworks: {clean}; each rework: −{rework}\n"
              "• missed daily report: −{missed} (at most −{missed_max} per task)",
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
