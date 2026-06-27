# 🔗 Telegram Bot - Platform Integratsiyasi

## 📋 Umumiy Qo'llanma

AiPlatforma foydalanuvchilari o'z Telegram hisoblarini platform hisobiga bog'lab, roli va profili ma'lumotlari bilan Telegram bot-dan foydalanishi mumkin.

---

## 🎯 Linkage Flow (Bog'lanish Jarayoni)

```
1. Foydalanuvchi Platform-ga kiradi
   ↓
2. Profilida "Telegramga Bog'lan" tugmasini bosadi
   ↓
3. API token yaratadi (30 daqiqa valid)
   ↓
4. Telegram Bot-ga /link token bilan komanda yubora yoki linkni bosadi
   ↓
5. Bot token tekshiradi va hisobni bog'laydi
   ↓
6. Platform shuni ko'radi: user.telegram_chat_id = 521013738
   ↓
7. Bot foydalanuvchini biladi: "Bu Jahongir, roli: designer"
```

---

## 📱 API Endpoints

### 1️⃣ Linking Token Yaratish

**Endpoint:**
```
POST /api/users/{user_id}/telegram/link
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/users/abc123/telegram/link \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "telegram_link": "https://t.me/AiSupport1_bot?start=link_abc123xyz...",
  "message": "Click the link or open Telegram and send: /link abc123xyz...",
  "token": "abc123xyz..."
}
```

**Javob bilan nima qilish:**
- Linkni Telegram-ga jo'natish
- Yoki `/link token` buyrug'i yuboring

### 2️⃣ Bog'lanishni O'chirish

**Endpoint:**
```
POST /api/users/{user_id}/telegram/unlink
```

**Request:**
```bash
curl -X POST http://localhost:8000/api/users/abc123/telegram/unlink \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "message": "Telegram account unlinked"
}
```

---

## 🤖 Telegram Bot Buyruqlari

### `/start` - Bosh Menyu
```
👋 Xush kelibsiz AiPlatforma Telegram Bot-ga!

Mavjud buyruqlar:
🔗 /link - Platformaga bog'lash
🎯 /miniapp - Mini App-ni ochish
📤 /send <xabar> - Xabar yuborish
❓ /help - Yordam olish
```

### `/link` - Platformaga Bog'lash

**Bez token-i:**
```
/link
```
Bot javob beradı: Platformada tokenni oling va quyidagi komandani yuboring

**Token bilan:**
```
/link abc123xyz...
```

**Javob (muvaffaqiyatli):**
```
✅ Muvaffaqiyatli!

User: Jahongir Boburovich
Role: designer
```

### `/miniapp` - Mini App
```
🎯 Mini App

📱 Mini App-ni ochish
yoki
URL-ni copy qiling:
http://localhost:8000/telegram/miniapp
```

### `/send` - Xabar Yuborish
```
/send Salom, bu test xabaridir!
```

Bot javob beradı: ✅ Xabar qabul qilindi!

---

## 💾 Database Model

### User Table (Qo'shimcha Field)
```sql
telegram_chat_id VARCHAR(100) -- Telegram user ID (chat_id)
```

### Linking Service
```
pending_links: {
  "token_xyz": {
    "user_id": "abc123",
    "created_at": "2024-...",
    "expires_at": "2024-... (30 daqiqa keyingi)"
  }
}
```

---

## 🔄 Integration Scenarios

### Scenario 1: Foydalanuvchi Telegram Bot-dan Biror Nima Qildi
```
1. Bot: "Siz bog'langan emassiz, /link buyrug'i yuboring"
2. User: Platformaga kiradi, /link tokenni oladiaz
3. User: Telegramda /link token yubora
4. Bot: Token tekshiradi, hisobni bog'laydi
5. Bot: Endi foydalanuvchini biladi
```

### Scenario 2: Taskga Komment Va Bot Bildirishnomasi
```
1. Foydalanuvchi A: Platform-da Task-ga komment yozadi
2. System: Task-ni assign qilgan foydalanuvchiga bildir
3. System: Telegram chat_id-ni tekshiradi
4. Bot: Agar telegram_chat_id mavjud bo'lsa, xabar yubora
5. Bot: "✅ Task-da komment: ..."
```

### Scenario 3: Role Bilan Turli Bildirishnomalar
```
Boshli Rolleri:
- admin: Barcha notifications
- manager: Team notifications
- designer: O'zning tasks/projects
- client: Approved documents
- gip: Project notifications
- gip_assistant: Task assignments
- reviewer: Review notifications

Telegramda:
- User: "admin" roli
- Bot: "Siz adminsiz, 5 ta yangi approval kutmoqda"
```

---

## 🔐 Xavfsizlik

### Token Security
- ✅ 32-character random token (urlsafe)
- ✅ 30 daqiqa validity
- ✅ Single use (o'zgartirilgach o'chadi)
- ✅ User_id bilan bog'langan

### Telegram Chat ID
- ✅ User hisobiga saqlangan
- ✅ Faqat Bot API-ga jo'natiladi
- ✅ Public emas (private field)

### Best Practices
```python
# ❌ NOTO'G'RI
telegram_chat_id = request.query_params["chat_id"]  # Direct user input

# ✅ TO'G'RI
telegram_chat_id = update.effective_user.id  # Telegram verified
token = get_link_request(token)  # Verify token
if token and token.user_id == current_user.id:  # Verify ownership
    link_account(...)
```

---

## 📊 Logging Va Monitoring

### Linking Events
```log
INFO:app.services.telegram_bot:Linked Telegram @JahongirBoburovich (521013738) to platform account
INFO:app.services.telegram_linking:Generated linking token for user abc123def456
```

### Error Cases
```log
ERROR:app.services.telegram_linking:Error linking account: Token expired or invalid
WARNING:app.services.telegram_bot:Failed to link Telegram @user: Token expired
```

---

## 🧪 Test Cases

### Test 1: Linking Flow
```bash
# 1. Login to platform
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"pass123"}'

# 2. Create link token (copy token from response)
curl -X POST http://localhost:8000/api/users/USER_ID/telegram/link \
  -H "Authorization: Bearer ACCESS_TOKEN"

# 3. In Telegram bot
/link <token_from_step_2>

# 4. Verify in platform
curl http://localhost:8000/api/users/USER_ID \
  -H "Authorization: Bearer ACCESS_TOKEN"
# Check: "telegram_chat_id": "521013738"
```

### Test 2: Unlinking
```bash
curl -X POST http://localhost:8000/api/users/USER_ID/telegram/unlink \
  -H "Authorization: Bearer ACCESS_TOKEN"
```

### Test 3: Send Message to Linked User
```bash
# From platform, send telegram message
curl -X POST http://localhost:8000/api/telegram/send-message \
  -H "Content-Type: application/json" \
  -d '{"message":"Test xabari","parse_mode":"HTML"}'
```

---

## 📈 Future Enhancements

### Phase 1 (Done)
- ✅ Telegram Bot Setup
- ✅ Linking Service
- ✅ Mini App
- ✅ Basic Commands

### Phase 2 (Planned)
- 📅 Role-based Notifications
- 📅 Task Notifications
- 📅 Document Approvals
- 📅 Team Updates

### Phase 3 (Advanced)
- 🔮 Telegram Web App Integration
- 🔮 Inline Bot Queries
- 🔮 Callback Buttons
- 🔮 Media Sharing

---

## 🐛 Troubleshooting

### Problem: "Token expired or invalid"
```
Solution:
1. Platform-da yangi token yarating: /api/users/ID/telegram/link
2. Token 30 daqiqa amal qiladi
3. Vaqtda Telegramda /link <token> yuboring
```

### Problem: "User not found"
```
Solution:
1. Platform-da ruxsat olganingizni tekshiring
2. Token yangi yaratgan user uchun
3. Access token tugon bo'lsa, yangi oling
```

### Problem: "Already linked"
```
Solution:
1. Telegram bog'lanishi allaqachon mavjud
2. Qayta bog'lash uchun: /api/users/ID/telegram/unlink
3. Keyin yangi link yarating
```

### Problem: Bot "Chat not found" deyapti
```
Solution:
1. Bot-ga /start yubor (conversation boshlash)
2. Keyin /link token yubor
3. Conversation ochilgandan so'ng xabar yuboriladi
```

---

## 📞 API Summary

| Method | Endpoint | Vazifa |
|--------|----------|--------|
| POST | `/api/users/{id}/telegram/link` | Link token yaratish |
| POST | `/api/users/{id}/telegram/unlink` | Linki o'chirish |
| POST | `/api/telegram/send-message` | Xabar yuborish |
| POST | `/api/telegram/send-notification` | Bildirishnoma |
| GET | `/api/telegram/info` | Bot ma'lumotlari |

---

## 📚 Related Files

- `backend/app/services/telegram_linking.py` - Linking logic
- `backend/app/services/telegram_bot.py` - Bot handlers
- `backend/app/routers/users.py` - User endpoints
- `backend/app/routers/telegram.py` - Telegram endpoints
- `backend/app/models/user.py` - User model

---

**Version**: 1.0.0  
**Last Updated**: 2024  
**Status**: ✅ Production Ready

Qo'shimcha savol bo'lsa: [Telegramda @JahongirBoburovich]
