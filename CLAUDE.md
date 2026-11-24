# AiPlatforma (GASTEC) — loyiha qoidalari

Qurilish kompaniyasi uchun loyiha boshqaruvi platformasi. Bitta Django 6 ilova:
server-rendered shablonlar, minimal vanilla JS, alohida frontend yo'q.

## Tuzilma
- `aiplatforma/settings/` — `base.py`, `dev.py` (testlar shu bilan), `prod.py`.
- `apps/<app>/` — accounts, projects, tasks, documents, finance, pult, reports,
  requests_app, organization, notifications, telegram_bot, ai_agents, core.
- `templates/<app>/` — shablonlar; `templates/base.html` umumiy layout.
- `static/css/tailwind.css` — Tailwind oldindan qurilgan va repoda saqlanadi.
  Shablonga yangi klass qo'shilsa, qayta qurish kerak:
  `tailwindcss -i static/css/src/input.css -o static/css/tailwind.css --minify`.
- `locale/uz`, `locale/ru` — tarjimalar (asosiy til o'zbek, rus ham to'liq).

## Konventsiyalar
- Kod izohlari o'zbek tilida. Foydalanuvchiga ko'rinadigan matnlar inglizcha
  msgid bilan `gettext`/`{% trans %}` orqali yoziladi, tarjimasi uz va ru
  .po fayllariga qo'shiladi.
- Ruxsatlar `User.role` orqali: `apps.core.permissions.role_required(...)`.
  Django'ning is_staff/Group tizimi faqat /django-admin/ uchun.
- Tokenlar va API kalitlar `settings.X` emas, `apps.core.runtime_config.get_config("X")`
  orqali o'qiladi (admin panelda shifrlangan saqlanadi).
- Celery vazifalari dev/testda sinxron (`CELERY_TASK_ALWAYS_EAGER`).
- UI: mavjud komponent klasslari (`card`, `btn btn-primary`, `badge badge-*`,
  `field-input`, `field-label`) va dark mode (`dark:`) variantlari.

## Tekshirish
- Testlar: `python manage.py test apps.<app>` (hammasi: `python manage.py test`).
- Model o'zgarsa: `python manage.py makemigrations`.
- Deploy: `docker compose up -d --build` (entrypoint migrate va collectstatic qiladi).
- `deploy/devbot/` — Telegram orqali kod o'zgartiruvchi bot (README ichida).
