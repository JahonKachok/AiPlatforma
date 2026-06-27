# ⚡ Telegram Bot - Tez Boshlash

## 🎯 Tahsisiy Konfiguratsiya

**Token**: `8779074840:AAFVmrVO8CWClN5DXKTFiy4rKqIKtUMhLys`  
**User ID**: `521013738`  
**Username**: @JahongirBoburovich

---

## 🚀 Boshlash (5 Minut)

### 1️⃣ Environment Setup
```bash
cd backend
# .env fayliga allaqachon qo'shildi!
cat .env | grep TELEGRAM
```

✅ Natija:
```
TELEGRAM_BOT_TOKEN=8779074840:AAFVmrVO8CWClN5DXKTFiy4rKqIKtUMhLys
TELEGRAM_WEBHOOK_URL=http://localhost:8000
TELEGRAM_USER_ID=521013738
```

### 2️⃣ Docker-compose Ishlatish
```bash
# Root direktoriyadan
docker-compose up -d

# Logs ko'rish
docker-compose logs -f backend
```

### 3️⃣ Integratsiyani Tekshirish

**Test xabari yuborish:**
```bash
curl -X POST http://localhost:8000/api/telegram/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Salom! <b>AiPlatforma</b>dan test xabari.",
    "parse_mode": "HTML"
  }'
```

**Natija:**
```json
{"ok": true, "message": "Message sent successfully"}
```

---

## 📲 Telegram Bot Buyruqlari

Telegramda @BotFather orqali yaratilgan botingizga quyidagi buyruqlarni yuboring:

```
/start         - Menu va mini app
/miniapp       - Mini app-ni ochish
/send <text>   - Xabar yuborish
```

---

## 🎨 Mini App

Mini App HTML: `backend/telegram_miniapp.html`

**Xususiyatlari:**
- ✨ Responsive Design
- 📤 Xabar yuborish (HTML/Markdown)
- 📊 Statistika
- 🔄 Real-time Updates

**Ochish:**
```
Telegram-da: /start → "🎯 Mini App" tugmasini bosing
```

---

## 📡 API Endpoints

### Xabar Yuborish
```bash
POST /api/telegram/send-message
{
  "message": "Xabar matni",
  "parse_mode": "HTML"
}
```

### Bildirishnoma Yuborish
```bash
POST /api/telegram/send-notification
{
  "title": "Sarlavha",
  "description": "Izoh",
  "notification_type": "success"  // info, warning, error, success
}
```

### Bot Ma'lumotlari
```bash
GET /api/telegram/info
```

### Webhook O'rnatish (Production)
```bash
POST /api/telegram/set-webhook?webhook_url=https://yourdomain.com/api/telegram/webhook
```

---

## 🐍 Python Kodi Namunalari

### Xabar Yuborish
```python
from app.services.telegram_service import telegram_service

await telegram_service.send_message(
    chat_id="521013738",
    text="<b>Salom!</b> Bu test.",
    parse_mode="HTML"
)
```

### Vazifa Bildirishnomasi
```python
await telegram_service.send_task_notification(
    chat_id="521013738",
    task_title="Loyihani tayyor qil",
    task_id="12345",
    action="yaratildi"
)
```

### Muddati Shunorovlantirish
```python
await telegram_service.send_deadline_reminder(
    chat_id="521013738",
    title="Loyiha Muddati",
    deadline="2024-12-31"
)
```

### Fayl Yuborish
```python
await telegram_service.send_file(
    chat_id="521013738",
    file_path="/path/to/file.pdf",
    caption="Fayl izohni"
)
```

---

## ✅ Tekshiruv Skripti

```bash
cd backend
python test_telegram.py
```

**Natija:**
```
🧪 Testing Telegram Integration...

✅ Telegram service initialized

🤖 Bot Info:
   Username: @YourBotName
   Name: Your Bot
   Bot ID: 123456789

📨 Sending test message to 521013738...
✅ Message sent successfully!
```

---

## 📚 Fayllar Struktura

```
AiPlatforma/
├── backend/
│   ├── app/
│   │   ├── services/
│   │   │   ├── telegram_service.py      # Xabar yuborish
│   │   │   └── telegram_bot.py          # Bot handlers (NEW)
│   │   ├── routers/
│   │   │   └── telegram.py              # API endpoints (NEW)
│   │   ├── config.py                    # TELEGRAM_USER_ID (UPDATED)
│   │   └── main.py                      # Bot initialization (UPDATED)
│   ├── .env                              # Tokens (UPDATED)
│   ├── .env.example                      # Template (UPDATED)
│   ├── telegram_miniapp.html             # Mini App (NEW)
│   └── test_telegram.py                  # Test script (NEW)
├── docker-compose.yml                    # Telegram env (UPDATED)
├── TELEGRAM_BOT.md                       # Full documentation (NEW)
└── TELEGRAM_QUICKSTART.md                # This file
```

---

## 🔧 Troubleshooting

### "Telegram bot not configured"
```bash
# .env fayilini tekshiring
cat backend/.env | grep TELEGRAM_BOT_TOKEN

# Qayta ishga tushiring
docker-compose restart backend
```

### "Failed to send message"
```bash
# User ID to'g'riligini tekshiring
echo "Your User ID: 521013738"

# Logs ni ko'ring
docker-compose logs backend
```

### "Webhook errors"
```bash
# Webhook status
curl https://api.telegram.org/bot8779074840:AAFVmrVO8CWClN5DXKTFiy4rKqIKtUMhLys/getWebhookInfo | python -m json.tool

# Webhook o'chirish
curl -X POST https://api.telegram.org/bot8779074840:AAFVmrVO8CWClN5DXKTFiy4rKqIKtUMhLys/deleteWebhook
```

---

## 🔒 Xavfsizlik

⚠️ **Muhim!**

1. Token-ni hech qachon publiclyga ko'rsatmang
2. `.env` faylini `.gitignore`-ga qo'shing
3. Production-da HTTPS foydalaning
4. Webhook URL-ni himoya qiling

---

## 📞 Qo'shimcha Yordam

- [Telegram Bot API Docs](https://core.telegram.org/bots/api)
- [Mini Apps](https://core.telegram.org/bots/webapps)
- [Python Telegram Bot](https://python-telegram-bot.readthedocs.io/)

---

## 🎉 Tayyor!

Endi siz quyidagilarni qilishingiz mumkin:

✅ Telegramda xabar yuborish  
✅ Mini App-da foydalanuvchi bilan o'zaro ta'sir  
✅ Avtomatik bildirishnomalar  
✅ Fayl yuborish  
✅ Webhook bilan bog'lanish

**Boshlanish uchun:**
```bash
docker-compose up -d
```

**Birinchi xabar yuborish:**
```bash
curl -X POST http://localhost:8000/api/telegram/send-message \
  -H "Content-Type: application/json" \
  -d '{"message": "Salom Jahongir!", "parse_mode": "HTML"}'
```

---

**Konfiguratsiya**: ✅ Tayyor  
**Test**: ✅ Tayyor  
**Production**: 🔧 Webhook URL-ni o'rnatish kerak

Savollar bo'lsa, `TELEGRAM_BOT.md` faylini o'qing! 📖
