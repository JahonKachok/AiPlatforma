# BuildFlow — ishga tushirish qo'llanmasi

## A. Serverda ishga tushirish (Docker, tavsiya etiladi)

**Talablar:** Ubuntu/Debian server, Docker va Docker Compose o'rnatilgan.

**1. Loyihani yuklab olish:**

```bash
git clone https://github.com/JahonKachok/AiPlatforma.git
cd AiPlatforma
```

**2. Sozlamalar faylini tayyorlash:**

```bash
cp .env.example .env
nano .env
```

`.env` ichida quyidagilarni to'ldiring:

```
SECRET_KEY=yangi-kuchli-maxfiy-kalit-kiriting
ALLOWED_HOSTS=sizning-domen.uz,server-ip-manzili
DEBUG=False

DATABASE_URL=postgres://aiplatforma:aiplatforma123@db:5432/aiplatforma
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
SECURE_SSL_REDIRECT=False

POSTGRES_DB=aiplatforma
POSTGRES_USER=aiplatforma
POSTGRES_PASSWORD=kuchli-parol-kiriting

TELEGRAM_BOT_TOKEN=botfather-bergan-token
TELEGRAM_BOT_USERNAME=bot_username

GEMINI_API_KEY=gemini-api-kalit
```

**3. Ishga tushirish (bitta buyruq — sayt, Telegram bot, AI, hammasi birga):**

```bash
docker compose up -d --build
```

**4. Birinchi admin foydalanuvchini yaratish:**

```bash
docker compose exec web python manage.py createsuperuser
```

**5. Tekshirish:**

- Sayt: `http://server-ip/` (nginx, 80-port)
- Holat: `docker compose ps` — 7 xizmat ham `running` bo'lishi kerak
- Loglar: `docker compose logs -f web` (yoki `telegram-bot`, `celery-beat`)

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
2. **HTTPS sozlagach** `.env`da `SECURE_SSL_REDIRECT=True` qiling.
3. **AI kunlik hisoboti** har kuni soat 8:00 da (Toshkent vaqti) admin va
   rahbarlarga sayt/email/Telegram orqali boradi.
   Qo'lda sinash: `python manage.py run_ai_agent`
4. `.env` faylini **hech qachon** git'ga qo'shmang — u allaqachon `.gitignore`da.
