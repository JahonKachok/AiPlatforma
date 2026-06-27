# 🤖 Telegram Bot Integration Guide

## Tahsisiy Ma'lumotlar

- **Bot Token**: `8779074840:AAFVmrVO8CWClN5DXKTFiy4rKqIKtUMhLys`
- **User ID**: `521013738`
- **Username**: @JahongirBoburovich

---

## Xususiyatlar

✅ **Mini App** - Telegram ichida veb-interfeys  
✅ **Xabar yuborish** - API orqali foydalanuvchiga xabar yuborish  
✅ **Bildirishnomalar** - Avtomatik bildirishnomalar  
✅ **Webhook yoki Polling** - Ikkala rejim qo'llab-quvvatlanadi  

---

## O'rnatish va Konfiguratsiya

### 1️⃣ Environment Variables

`backend/.env` fayliga quyidagilarni qo'shing:

```bash
TELEGRAM_BOT_TOKEN=8779074840:AAFVmrVO8CWClN5DXKTFiy4rKqIKtUMhLys
TELEGRAM_WEBHOOK_URL=http://localhost:8000
TELEGRAM_USER_ID=521013738
```

### 2️⃣ Dependentlarni O'rnatish

```bash
cd backend
pip install -r requirements.txt
```

Requirements.txt-da `python-telegram-bot==21.9` allaqachon mavjud.

### 3️⃣ Docker-compose Ishlatish

```bash
docker-compose up -d
```

Bot avtomatik ravishda ishga tushadi.

---

## API Endpoints

### 📨 Xabar Yuborish

**POST** `/api/telegram/send-message`

```json
{
  "message": "Salom! Bu test xabaridir.",
  "parse_mode": "HTML"
}
```

**Response:**
```json
{
  "ok": true,
  "message": "Message sent successfully"
}
```

### 🔔 Bildirishnoma Yuborish

**POST** `/api/telegram/send-notification`

```json
{
  "title": "Vazifa Tayyor",
  "description": "Sizning vazifangiz bajarildi!",
  "notification_type": "success"
}
```

**Notification Types**: `info`, `warning`, `error`, `success`

### 🤖 Bot Ma'lumotlarini Olish

**GET** `/api/telegram/info`

**Response:**
```json
{
  "username": "YourBotName",
  "name": "Your Bot",
  "user_id": "521013738"
}
```

### 🔗 Webhook O'rnatish

**POST** `/api/telegram/set-webhook?webhook_url=https://yourdomain.com/api/telegram/webhook`

### 🗑️ Webhook O'chirish

**DELETE** `/api/telegram/remove-webhook`

---

## Telegram Mini App

Mini App HTML fayly:  
📁 `backend/telegram_miniapp.html`

### Mini App Xususiyatlari:

- ✨ **Responsive Design** - Barcha qurilmalarda ishlaydi
- 📤 **Xabar yuborish** - HTML/Markdown formatlashni qo'llab-quvvatlanadi
- 📊 **Statistika** - Xabar va bildirishnomalar soni
- 🔄 **Real-time Updates** - API bilan bog'lanish
- 🎨 **Modern UI** - Gradient va animatsiyalar

### Mini App Links:

```
/start - Mini app-ni ochish
/miniapp - Mini app-ni ochish
/send <text> - Xabar yuborish
```

---

## Python Service Namunalari

### Telegram Service (Xabarlash)

```python
from app.services.telegram_service import telegram_service

# Xabar yuborish
await telegram_service.send_message(
    chat_id="521013738",
    text="<b>Salom!</b> Bu test xabaridir.",
    parse_mode="HTML"
)

# Fayl yuborish
await telegram_service.send_file(
    chat_id="521013738",
    file_path="/path/to/file.pdf",
    caption="Bu sizning faylingiz"
)

# Vazifa bildirishnomasi
await telegram_service.send_task_notification(
    chat_id="521013738",
    task_title="Loyihani tayyor qil",
    task_id="12345",
    action="yaratildi"
)
```

### Telegram Bot (Update Handler)

```python
from app.services.telegram_bot import telegram_bot

# Bot o'rnatish
await telegram_bot.initialize()

# Update qayta ishlash
await telegram_bot.process_update(update_data)
```

---

## Webhook o'rnatish (Production)

### 1️⃣ Domen nomini hozirla

```bash
https://yourdomain.com
```

### 2️⃣ Webhook URL-ni o'rnatish

```bash
curl -X POST "https://yourdomain.com/api/telegram/set-webhook?webhook_url=https://yourdomain.com/api/telegram/webhook"
```

### 3️⃣ SSL Sertifikatini O'rnatish

Webhook HTTPS bilan ishlashi kerak. Self-signed sertifikat qo'llashingiz mumkin:

```bash
openssl req -newkey rsa:2048 -sha256 -nodes -out server.crt -keyout server.key -x509 -days 365
```

---

## Debugging

### Bot holati tekshirish

```bash
# Container logs
docker-compose logs backend

# Bot ma'lumotlari
curl http://localhost:8000/api/telegram/info
```

### Webhook status

```bash
# Telegram dan webhook status
https://api.telegram.org/bot8779074840:AAFVmrVO8CWClN5DXKTFiy4rKqIKtUMhLys/getWebhookInfo
```

---

## Xavfsizlik

⚠️ **Muhim!**

- Token-ni PublicDirectory-ga ko'rsatmang
- `.env` faylini `.gitignore`-ga qo'shing
- Production-da HTTPS ishlatishi shart
- Webhook URL-ni hifoya qiling

---

## Qo'shimcha Resurslar

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Telegram Mini Apps](https://core.telegram.org/bots/webapps)
- [python-telegram-bot Dokumentatsiya](https://python-telegram-bot.readthedocs.io/)

---

## Muammoni Hal Qilish

### "Telegram bot token not configured"

✓ `.env` faylida TELEGRAM_BOT_TOKEN-ni tekshiring

### "Failed to initialize Telegram bot"

✓ Token-ning to'g'riligini tekshiring  
✓ Internet ulanishini tekshiring

### "Webhook processing failed"

✓ Webhook URL-ni tekshiring  
✓ Sertifikatni tekshiring (HTTPS)

---

## Foydalanuvchi Reaksiyalari

Xabar yuborish:

```bash
curl -X POST http://localhost:8000/api/telegram/send-message \
  -H "Content-Type: application/json" \
  -d '{"message": "Salom!", "parse_mode": "HTML"}'
```

Bildirishnoma yuborish:

```bash
curl -X POST http://localhost:8000/api/telegram/send-notification \
  -H "Content-Type: application/json" \
  -d '{"title": "Tayyor!", "description": "Vazifa tugadi", "notification_type": "success"}'
```

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Developer**: AiPlatforma Team
