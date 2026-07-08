# AiPlatforma

Construction-company project management platform: projects, tasks (kanban/list/calendar), document approval workflows, finance, requests, document-generation templates, organization chart, and Telegram bot notifications. Built as a single Django app (server-rendered templates, minimal vanilla JS) — no separate frontend/backend split.

## Stack

- Django 6 (server-rendered templates, session auth, 2FA via TOTP)
- SQLite by default (`DATABASE_URL` env var to switch to Postgres)
- Celery + Redis for background jobs (deadline reminders, email/Telegram delivery)
- Tailwind CSS (compiled ahead of time; no Node needed at runtime)
- `python-telegram-bot` for the Telegram integration

## Local development

```bash
python -m venv .venv
.venv\Scripts\activate          # or `source .venv/bin/activate` on Linux/macOS
pip install -r requirements.txt

copy .env.example .env          # fill in SECRET_KEY etc.
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo_data # optional: realistic demo data

python manage.py runserver
```

Visit `http://localhost:8000`. Django admin is at `/django-admin/`.

### CSS

Tailwind output is checked into `static/css/tailwind.css` (built ahead of time — no Node needed to *run* the app, only to rebuild the CSS after changing templates or `static/css/src/input.css`):

```bash
npm install --no-save tailwindcss @tailwindcss/cli
npx tailwindcss -i static/css/src/input.css -o static/css/tailwind.css --minify
```

### Background jobs (Celery)

In dev, `CELERY_TASK_ALWAYS_EAGER=True` runs tasks synchronously — no Redis/worker needed for `runserver` or `manage.py test`. For real async behavior (e.g. testing the deployment setup), run Redis plus:

```bash
celery -A aiplatforma worker --loglevel=info
celery -A aiplatforma beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
python manage.py setup_periodic_tasks   # registers the hourly deadline-check task
```

### Telegram bot

Set `TELEGRAM_BOT_TOKEN` (and `TELEGRAM_BOT_USERNAME`) in `.env`, then run the bot as its own long-running process:

```bash
python manage.py run_telegram_bot
```

### Tests

```bash
python manage.py test apps
```

## Deployment

`docker-compose.yml` runs the full stack: `web` (gunicorn), `celery-worker`, `celery-beat`, `telegram-bot`, `redis`, and `nginx` (reverse proxy + static/media serving). Copy `.env.example` to `.env` with real production values first, then:

```bash
docker compose up -d --build
```
