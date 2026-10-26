# BuildFlow — ishga tushirish qo'llanmasi

## A. Serverda ishga tushirish (Docker, tavsiya etiladi)

**Talablar:** Ubuntu 22.04/24.04 VPS (kamida 2 GB RAM), domen.

**1. Domen DNS'i:** domen provayderida `example.uz` va `www.example.uz` uchun
A-yozuvni server IP manziliga qarating (www kerak bo'lmasa, uni qo'shmang va
`.env` da `LETSENCRYPT_WWW=0` qiling).

**2. Loyihani yuklab olish va serverni himoyalash (bir marta):**

```bash
git clone https://github.com/JahonKachok/AiPlatforma.git
cd AiPlatforma
sudo sh deploy/server-setup.sh
```

Bu skript tizimni yangilaydi, Docker, 2 GB swap, firewall (faqat SSH/80/443),
fail2ban va avtomatik xavfsizlik yangilanishlarini o'rnatadi. Serverga SSH
kalit qo'shilgan bo'lsa, parol bilan kirishni o'chiradi. Kalit bo'lmasa, avval
`ssh-copy-id` bilan kalit qo'shib, skriptni qayta ishga tushirish tavsiya
etiladi.

**3. Sozlamalar faylini tayyorlash:**

```bash
cp .env.example .env
nano .env
```

`.env` ichida "Docker/server rejimi" bo'limidagi qatorlarni izohdan chiqarib
to'ldiring, ayniqsa:

```
SECRET_KEY=...                 # python3 -c "import secrets; print(secrets.token_urlsafe(64))"
DEBUG=False
DOMAIN=example.uz
LETSENCRYPT_EMAIL=admin@example.uz
ALLOWED_HOSTS=example.uz,www.example.uz
CSRF_TRUSTED_ORIGINS=https://example.uz
FRONTEND_URL=https://example.uz
SECURE_SSL_REDIRECT=True
POSTGRES_PASSWORD=...          # DATABASE_URL ichidagi parol bilan bir xil
DATABASE_URL=postgres://aiplatforma:<POSTGRES_PASSWORD>@db:5432/aiplatforma
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
TELEGRAM_BOT_TOKEN=...
GEMINI_API_KEY=...
```

Faylni boshqalar o'qiy olmasin: `chmod 600 .env`

**4. HTTPS sertifikatini olish va hammasini ishga tushirish:**

```bash
docker compose build
sh deploy/init-letsencrypt.sh
docker compose up -d
```

Sertifikat har 12 soatda tekshiriladi va muddati yaqinlashganda `certbot`
konteyneri tomonidan avtomatik yangilanadi.

**5. Birinchi admin foydalanuvchini yaratish:**

```bash
docker compose exec web python manage.py createsuperuser
```

**6. Tekshirish:**

- Sayt: `https://example.uz/` (http avtomatik https'ga yo'naltiriladi)
- Holat: `docker compose ps` — barcha xizmatlar `running` bo'lishi kerak
- Loglar: `docker compose logs -f web` (yoki `telegram-bot`, `celery-worker`)

**Baza nusxalari (backup):** `db-backup` konteyneri har kuni Postgres
nusxasini oladi va 14 kun saqlaydi (`BACKUP_KEEP_DAYS`). Ro'yxat:
`docker compose exec db-backup ls -lh /backups`. Saytdagi Profil → Backups
(faqat admin) media fayllar va eng oxirgi baza nusxasini bitta zip qiladi.
Nusxalarni vaqti-vaqti bilan serverdan tashqariga ham ko'chirib turing.
Tiklash buyrug'i `deploy/db-backup.sh` boshida yozilgan.

**Boshqarish buyruqlari:**

```bash
docker compose down          # to'xtatish
docker compose up -d         # qayta yoqish
docker compose restart web   # bitta xizmatni qayta yuklash
docker compose logs -f       # barcha loglarni kuzatish
```

---

## B. Oddiy kompyuterda test qilish (Windows, Dockersiz)

**Talablar:** Python 3.12+, loyiha papkasida `.venv` tayyor bo'lishi.

**1. Birinchi marta (faqat bir marta):**

```powershell
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
# .env ichida SECRET_KEY, GEMINI_API_KEY, TELEGRAM_BOT_TOKEN ni to'ldiring
.venv\Scripts\python manage.py migrate
.venv\Scripts\python manage.py createsuperuser
```

**2. Hammasini birga ishga tushirish:**

```powershell
.\start-dev.ps1
```

Bu bitta buyruq 4 ta jarayonni ochadi: Django server (http://localhost:8000),
Telegram bot, Celery worker va Celery beat (kunlik 8:00 dagi AI hisobot).

**3. To'xtatish:**

```powershell
.\stop-dev.ps1
```

---

## Muhim eslatmalar

1. **Telegram bot faqat bitta joyda ishlasin** — serverda yoqsangiz,
   kompyuterdagisini to'xtating (ikkalasi bir vaqtda xabar talashib xato beradi).
2. **Ochiq ro'yxatdan o'tgan** foydalanuvchilar nofaol yaratiladi — ularni
   admin yoki menejer Foydalanuvchilar sahifasida faollashtiradi.
3. **AI kunlik hisoboti** har kuni soat 8:00 da (Toshkent vaqti) admin va
   rahbarlarga sayt/email/Telegram orqali boradi.
   Qo'lda sinash: `python manage.py run_ai_agent`
4. **Yangilash:** `git pull && docker compose up -d --build`
5. `.env` faylini **hech qachon** git'ga qo'shmang — u allaqachon `.gitignore`da.
