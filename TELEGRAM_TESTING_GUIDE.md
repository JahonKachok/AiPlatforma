# 🧪 Telegram Bot - Testing Guide

## ✅ End-to-End Testing

### Phase 1: Bot Buyruqlari (Telegram-da)

#### Step 1: Bot-ni Boshlash
```
Telegram-da: /start

Expected Response:
👋 Xush kelibsiz AiPlatforma Telegram Bot-ga!

Mavjud buyruqlar:
🔗 /link - Platformaga bog'lash
🎯 /miniapp - Mini App-ni ochish
📤 /send <xabar> - Xabar yuborish
❓ /help - Yordam olish
```

#### Step 2: Help Komandasi
```
Telegram-da: /help

Expected Response:
🤖 Telegram Bot Buyruqlari

Asosiy:
/start - Bosh menyu
/help - Bu xabar

Bog'lash:
/link - Platformaga bog'lash

Xabarlar:
/send <text> - Xabar yuborish

Mini App:
/miniapp - Mini App-ni ochish

Izoh:
Bot har qanday xabarga echo bilan javob beradi.
```

#### Step 3: Echo Test
```
Telegram-da: Salom Bot!

Expected Response:
✅ Xabaringiz qabul qilindi!

Matni: Salom Bot!
```

#### Step 4: Mini App Komandasi
```
Telegram-da: /miniapp

Expected Response:
🎯 Mini App

📱 Mini App-ni ochish
yoki
URL-ni copy qiling:
http://localhost:8000/telegram/miniapp

[Linkni bosing]
```

---

### Phase 2: Linking Test (Asosiy)

#### Step 2.1: Platform-da Token Yaratish

**Via cURL:**
```bash
# Avval login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@platform.uz",
    "password": "admin123"
  }'

# Response-dan access_token-ni oling, keyin:
TOKEN="your_access_token"
USER_ID="user_id_from_response"

# Link token yaratish
curl -X POST http://localhost:8000/api/users/$USER_ID/telegram/link \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "telegram_link": "https://t.me/AiSupport1_bot?start=link_abc123xyz...",
  "message": "Click the link or open Telegram and send: /link abc123xyz...",
  "token": "abc123xyz..."
}
```

#### Step 2.2: Telegram-da Link Komandasi

```
Telegram-da: /link abc123xyz...

Expected Response:
✅ Muvaffaqiyatli!

User: Jahongir Boburovich
Role: admin
```

#### Step 2.3: Linking-ni Tekshirish

```bash
# User ma'lumotlarini olish
curl http://localhost:8000/api/users/$USER_ID \
  -H "Authorization: Bearer $TOKEN"

# Response-da ko'rish kerak:
"telegram_chat_id": "521013738"
```

---

### Phase 3: Xabar Yuborish

#### Step 3.1: API orqali Xabar

```bash
curl -X POST http://localhost:8000/api/telegram/send-message \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test xabari",
    "parse_mode": "HTML"
  }'
```

**Expected:**
- ✅ Response: {"ok": true, "message": "Message sent successfully"}
- ✅ Telegram-da: Xabar qabul qilindi

#### Step 3.2: Bildirishnoma Yuborish

```bash
curl -X POST http://localhost:8000/api/telegram/send-notification \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Bildirishnoma",
    "description": "Bu test bildirishnomasi",
    "notification_type": "success"
  }'
```

**Expected:**
- ✅ Response: {"ok": true}
- ✅ Telegram-da: ✅ Test Bildirishnoma

---

### Phase 4: Mini App Test

#### Step 4.1: Browser-da Ochish
```
http://localhost:8000/telegram/miniapp
```

**Expected:**
- ✅ Modern UI ko'rinadi
- ✅ Xabar yuborish input mavjud
- ✅ Info tab-i
- ✅ Tugmalar ishga tushadi

#### Step 4.2: Xabar Yuborish Mini App-dan

1. Mini App-da text kiritish:
```
Test xabari mini app-dan
```

2. "Yuborish" tugmasini bosing

3. Expected:
- ✅ Success alert: "Xabar muvaffaqiyatli yuborildi!"
- ✅ Input cleared
- ✅ Telegram-da xabar qabul qilindi

#### Step 4.3: Info Tab
1. "ℹ️ Ma'lumot" tab-ni bosing
2. Expected:
- ✅ Bot statistikasi ko'rinadi
- ✅ Bot ma'lumotlari (username, ID)
- ✅ Refresh tugmasi ishlaydi

---

### Phase 5: Advanced Tests

#### Test 5.1: Multiple Users Linking

```bash
# User 1
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user1@example.com",
    "password": "pass123"
  }'

# User 1 uchun link yaratish va Telegram-da linking

# User 2
# Same process with different user

# Expected: Har bir user o'z telegram_chat_id-ga ega
```

#### Test 5.2: Unlinking

```bash
# Linking-ni o'chirish
curl -X POST http://localhost:8000/api/users/$USER_ID/telegram/unlink \
  -H "Authorization: Bearer $TOKEN"

# Expected Response:
{"message": "Telegram account unlinked"}

# Verify:
curl http://localhost:8000/api/users/$USER_ID \
  -H "Authorization: Bearer $TOKEN"
# "telegram_chat_id": null
```

#### Test 5.3: Token Expiration

```bash
# 1. Token yaratish
curl -X POST http://localhost:8000/api/users/$USER_ID/telegram/link \
  -H "Authorization: Bearer $TOKEN"

# 2. 30 daqiqani kutish (yoki test-da simulate qilish)

# 3. Expired token bilan /link yuboring
/link expired_token_xyz

# Expected Response:
❌ Token expired or invalid
```

#### Test 5.4: Role-based Responses

**Admin User:**
```
Telegram-da: /link token

Expected:
✅ Muvaffaqiyatli!

User: Admin User
Role: admin
```

**Designer User:**
```
Telegram-da: /link token

Expected:
✅ Muvaffaqiyatli!

User: Designer User
Role: designer
```

---

## 🔧 Debugging

### Backend Logs

```bash
# Docker-da (agar Docker ishga tushgan bo'lsa)
docker-compose logs -f backend

# Yuklashda search:
- "Bot polling started successfully"
- "Linked Telegram @username"
- "Failed to send message"
```

### Telegram Bot Debug

```
Expected flows in logs:

1. Bot start
   INFO:telegram.ext.Application:Application started
   INFO:app.services.telegram_bot:Bot polling started successfully

2. User sends message
   INFO:httpx:HTTP Request: ... /getUpdates

3. Link command
   INFO:app.services.telegram_linking:Generated linking token
   INFO:app.services.telegram_bot:Linked Telegram @username
```

### API Debug

```bash
# Health check
curl http://localhost:8000/api/health

# Bot info
curl http://localhost:8000/api/telegram/info

# User data
curl http://localhost:8000/api/users/{id} \
  -H "Authorization: Bearer $TOKEN"
```

---

## ✅ Test Checklist

### Bot Commands
- [ ] `/start` - Bot javob beradi
- [ ] `/help` - Help matni ko'rsatiladi
- [ ] `/link` - Token olamiz (to'g'ri message)
- [ ] `/link token` - Linking muvaffaqiyatli
- [ ] `/miniapp` - Mini App URL ko'rsatiladi
- [ ] `/send text` - Echo javob
- [ ] Random text - Echo javob

### Linking Flow
- [ ] Platform-da token yaratiladi
- [ ] Token 30 daqiqa valid
- [ ] Telegram-da linking muvaffaqiyatli
- [ ] User.telegram_chat_id yangilandi
- [ ] Qayta linking uchun unlink kerak
- [ ] Unlink successful
- [ ] Yangi link yaratish mumkin

### Mini App
- [ ] URL yuklash ('404 emas)
- [ ] HTML ko'rsatiladi
- [ ] Xabar yuborish ishlaydi
- [ ] Info tab ishlaydi
- [ ] Refresh tugmasi ishlaydi
- [ ] Mobile responsive

### Error Cases
- [ ] Expired token error
- [ ] Invalid user error
- [ ] Already linked error
- [ ] Not linked error
- [ ] Chat not found error (fixed by /start)

### Security
- [ ] Token single-use
- [ ] Token time-limited
- [ ] User verification
- [ ] Role checking
- [ ] Authorization headers

---

## 📊 Test Results Template

```
Test Date: 2024-XX-XX
Tester: [Your Name]
Environment: Local/Docker/Production

=== Bot Commands ===
[✅/❌] /start
[✅/❌] /help
[✅/❌] /link
[✅/❌] /miniapp
[✅/❌] /send
[✅/❌] Echo

=== Linking ===
[✅/❌] Token Generation
[✅/❌] Token Validation
[✅/❌] Linking Success
[✅/❌] Database Update
[✅/❌] Unlinking

=== Mini App ===
[✅/❌] Load Page
[✅/❌] Send Message
[✅/❌] Show Info
[✅/❌] Responsive Design

=== Errors ===
[✅/❌] Token Expired
[✅/❌] Invalid User
[✅/❌] Chat Not Found

Notes:
...
```

---

## 🚀 Performance Test

### Load Test (Optional)

```bash
#!/bin/bash
# 10 ta xabar yuborish
for i in {1..10}; do
  curl -X POST http://localhost:8000/api/telegram/send-message \
    -H "Content-Type: application/json" \
    -d "{\"message\": \"Test $i\"}"
  sleep 1
done
```

**Expected:**
- ✅ Barcha xabarlar yuboriladi
- ✅ No timeout errors
- ✅ Performance acceptable

---

## 📝 Regression Testing

Har update-dan keyin quyidagilarni test qiling:

- [ ] Bot still responds
- [ ] Commands work
- [ ] Linking still works
- [ ] Mini App accessible
- [ ] API endpoints functional
- [ ] Database queries OK
- [ ] Logs clean (no errors)

---

## 🐛 Known Issues

### Issue: "Chat not found"
**Status:** ✅ Fixed  
**Solution:** Telegram-da /start yuboring  

### Issue: "Token expired"
**Status:** ✅ By Design  
**Solution:** Yangi token yarating (30 daqiqada)

### Issue: Multiple concurrent links
**Status:** ✅ Protected  
**Solution:** Unlink keyin link

---

## 📞 Support

**Bot Logs Checking:**
```bash
# Last 50 lines
tail -50 bot.log

# Search for errors
grep ERROR bot.log

# Real-time monitoring
tail -f bot.log
```

**Database Verification:**
```bash
# User telegram_chat_id tekshirish
sqlite3 platform.db "SELECT email, telegram_chat_id FROM users LIMIT 10;"

# Linking history (if stored)
sqlite3 platform.db "SELECT * FROM telegram_links LIMIT 10;"
```

---

**Test Guide Version**: 1.0.0  
**Last Updated**: 2024  
**Status**: ✅ Complete

Barcha testlar muvaffaqiyatli bo'lsa, production-ga ready! 🎉
