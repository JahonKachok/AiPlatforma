# Devbot — Telegram orqali platforma kodini o'zgartirish

Botga vazifani oddiy matn bilan yozasiz, masalan: *"Foydalanuvchilar jadvaliga
Excel'ga eksport tugmasini qo'sh"*. Izohli skrinshot yuborsangiz ham bo'ladi.

Claude Code kodni o'zgartiradi va testlarni o'tkazadi. Ish jarayoni Telegram'da
jonli ko'rinadi: 📖 fayllarni o'qiyapti, ✏️ tahrirlayapti, 💻 testlarni
ishlatyapti. Kerak bo'lsa ⏹ bilan to'xtatasiz.

Natija kelgach, javob yozib davom ettirasiz. Claude savol bersa, shunchaki
javob berasiz. **🚀 Deploy** tugmasini bosmaguningizcha ishlab turgan saytga
hech narsa tegmaydi.

Buyruqlar: `/new <matn>`, `/stop`, `/status`, `/log`, `/cancel`, `/rollback`.

## Sozlash: platformaning o'zidan

Sozlamalar **Profil → Integratsiyalar → Devbot** bo'limida kiritiladi. Bu
sahifani faqat adminlar ochadi.

| Maydon | Izoh |
|---|---|
| Devbot tokeni | @BotFather'dan **alohida** bot. Asosiy botning tokenini qo'yib bo'lmaydi. |
| Devbot nomi | Username, sahifada bot havolasi ko'rinadi. |
| Claude API kaliti | Bo'sh qolsa, yuqoridagi umumiy Claude kaliti ishlatiladi. |
| Claude modeli | Bo'sh qolsa, Claude Code standart modeli ishlatiladi. |

- Token o'zgartirilsa, devbot bir daqiqa ichida yangi token bilan qayta yoqiladi.
- **Buyruqni faqat Telegram'i profilga ulangan faol adminlar bera oladi.**
  Ularning ro'yxati shu sahifada ko'rinadi. Boshqa odam yozsa, bot rad etadi.
- Sahifada bot holati ham ko'rinadi: ishlayapti, vazifa bajaryapti, javob
  bermayapti yoki o'rnatilmagan.

## Serverga o'rnatish (bir marta)

Platforma papkasida:

```sh
sudo sh deploy/devbot/setup-devbot.sh
journalctl -u aiplatforma-devbot -f
```

So'ng panelda tokenni kiritasiz va hammasi tayyor. Devbot kodi yangilansa,
shu skriptni qayta ishga tushiring.

## Qanday ishlaydi

```
Telegram ──► devbot (systemd, serverda)
               │  sozlamalar: docker exec web manage.py devbot_config
               ▼
          ishchi klon  ~/.aiplatforma-devbot/work   (bot/<sana> branch)
               │
               ▼
          runner konteyner (web image + Claude Code + Tailwind CLI)
            • /work — faqat ishchi klon; .env, baza, docker socket YO'Q
            • RAM/CPU chegarasi, root huquqlarisiz
               │  🚀 Deploy
               ▼
          ishlab turgan papka: git merge --ff-only → docker compose up -d --build
            • web sog'lom bo'lmasa — avtomatik oldingi versiyaga qaytadi
```

- Claude'da shell bor: testlar, `makemigrations`, `compilemessages`,
  `tailwindcss`. Lekin u faqat runner konteyner ichida ishlaydi.
- Claude ishini tugatgach, bot quyidagilarni o'zi bajaradi: yetishmagan
  migratsiyani yaratadi, shablon o'zgargan bo'lsa `tailwind.css`ni qayta
  quradi, barcha testlarni tarmoqsiz ishga tushiradi.
- Claude sessiyalari `~/.aiplatforma-devbot/claude-home` papkasida saqlanadi,
  shuning uchun javob yozganingizda u avvalgi ishni eslaydi.
- Loyiha qoidalari repodagi `CLAUDE.md` faylida yozilgan, Claude uni har
  vazifada o'qiydi.

## Xavfsizlik

- Runner konteynerda internet bor, chunki Claude API'ga ulanishi kerak. Lekin
  u yerda maxfiy narsa yo'q: faqat kod va Claude kaliti.
- Bot tokeni va Claude kaliti platforma bazasida shifrlangan holda saqlanadi
  va sahifada hech qachon to'liq ko'rsatilmaydi.
- `/rollback` kodni qaytaradi, lekin **baza migratsiyalarini qaytarmaydi**.
  Model o'zgargan deploylarni ehtiyotkorlik bilan tasdiqlang. Bazaning kunlik
  nusxasi `db-backup` xizmatida saqlanadi.
- `DEVBOT_PUSH_TO_ORIGIN=0` bo'lsa, o'zgarishlar faqat serverda qoladi.
  Kompyuteringizda ishlashdan oldin serverdagi `main`ni GitHub'ga push qiling.
  Yoki yozish huquqli deploy key qo'shib, `/etc/aiplatforma-devbot.env` da
  `DEVBOT_PUSH_TO_ORIGIN=1` qiling.
