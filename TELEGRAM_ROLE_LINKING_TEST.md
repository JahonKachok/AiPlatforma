# 🔗 Telegram Bot - Role Linking Test Guide

## 🎯 Nima Tayyorlandi?

✅ **Platform-dan Telegram Bot-ga avtomatik rol bog'lanishi**

- Foydalanuvchi Platform-dan bog'langanida
- Bot avtomatik user.role-ni sync qiladi
- Turidagi bildirishnomalar role-ga qarab shaxsiylashtirilib yuboriladi

---

## 📝 Architecture

```
Frontend (Settings)
    ↓
    ├→ POST /api/users/{id}/telegram/link
    ↓
Backend (telegram_linking.py)
    ├→ Token yaratish
    ├→ user.role oqish
    ↓
Telegram Bot
    ├→ /link token komandasi
    ├→ User rol bilan link
    ├→ Message: "Role: designer" ko'rsatish
    ↓
Database
    └→ user.telegram_chat_id saqlanadi
       user.role = "designer" (already in DB)
```

---

## 🧪 Step-by-Step Test

### Step 1: Frontend Build Tekshirish
```bash
cd d:\github\AiPlatforma
npm run build
# ✅ Build successful (yarning warnings oqish mumkin)
```

### Step 2: Browser Refresh
```
F5 yoki Ctrl+Shift+R (cache clear)
URL: http://localhost:5173 yoki http://localhost:8000
```

### Step 3: Platform-da Login
```
Email:    test@platform.uz
Password: Test123456
Rol:      designer ✅
```

### Step 4: Settings → Integrations
```
Telegram: "Не подключено" ❌
```

### Step 5: "Подключить" tugmasini bosing
```
✨ Telegram bot link automatik ochiladi
```

### Step 6: Telegram-da /link komandasi
```
/start yuboring (conversation boshlash)

Keyin:
/link {token_from_settings}
```

### Step 7: Bot Javob Beradi
```
✅ Muvaffaqiyatli!

User: Test User
Role: designer    ← ROL AVTOMATIK QOSHLANDI! 🎯
```

### Step 8: Settings Yangilash
```
F5 yoki qayta Settings-ni oching
Telegram: "Подключено" ✅
Status: Linked with role
```

---

## 🔍 Validation Checks

### Backend Tekshiruvi
```bash
# User ma'lumotlarini oqish
curl http://localhost:8000/api/users/{user_id} \
  -H "Authorization: Bearer {access_token}"

# Response-da ko'rish kerak:
{
  "id": "2ba22802-...",
  "email": "test@platform.uz",
  "role": "designer",
  "telegram_chat_id": "521013738",  ← BOG'LANGAN!
  ...
}
```

### Telegram Bot Test
```
Bot-da /help yuboring
↓
Bot ko'rsatadi: "✨ Bot sizning rolni avtomatik taniy..."
↓
Bu tasdiqlaydi: Role support faol
```

---

## 📊 Expected Results

| Component | Status | Details |
|-----------|--------|---------|
| Frontend Build | ✅ | No errors |
| Platform Login | ✅ | test@platform.uz works |
| Telegram Link Button | ✅ | Clicks and opens bot |
| Bot /link Command | ✅ | Accepts token |
| Role Syncing | ✅ | Shows "Role: designer" |
| Database Update | ✅ | telegram_chat_id saved |
| Settings Reflection | ✅ | Shows "Подключено" |

---

## 🐛 Debugging

### Problem: Frontend link button not working
**Solution**: Browser cache clear (Ctrl+Shift+R)

### Problem: Bot doesn't respond
**Solution**: /start yuboring then /link {token}

### Problem: Role not showing
**Solution**: Backend logs tekshiring
```bash
docker-compose logs backend | grep -i telegram
```

### Problem: Settings doesn't update
**Solution**: Refresh page and re-login

---

## 🎯 Key Features

✅ **Automatic Role Linking**
- User Platform-dan bog'langanda
- Role avtomatik Telegram-da saqlanadi
- Keyingi bildirishnomalar role-aware bo'ladi

✅ **Dynamic Status Display**
- Settings-da real-time status
- Role info ko'rinadi
- Disconnect option mavjud

✅ **Security**
- Token-based linking (30 min valid)
- User ownership verified
- Database transaction safe

---

## 📱 Test Accounts

### Account 1 (Designer)
```
Email:    test@platform.uz
Password: Test123456
Role:     designer
```

### Account 2 (Admin)
```
Email:    admin@platform.uz
Password: admin123
Role:     admin
```

---

## ✨ Next Steps (Future)

- [ ] Role-based notifications
- [ ] Task assignment alerts
- [ ] Document approval notifications
- [ ] Team updates
- [ ] Mini App role integration

---

**Test Complete? Natijani ayting!** 🚀

✅ Everything works
❌ Something broken
⚠️ Partial working
