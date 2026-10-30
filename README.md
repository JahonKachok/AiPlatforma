# BuildFlow — Construction Automation Platform

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
python manage.py setup_pult_periodic_tasks  # Pult: 17:30 report reminder, 08:30 "waiting for your decision" digest
```

### AI agents (Claude)

The deadline-control AI agent (`apps/ai_agents`) summarizes overdue/upcoming tasks with Claude and notifies admins/managers. Set `ANTHROPIC_API_KEY` in `.env` (key from https://console.anthropic.com); without it, agents are silently skipped.

```bash
python manage.py run_ai_agent            # manual test run (prints the report; --send also notifies)
python manage.py setup_ai_periodic_tasks # registers the daily 08:00 Celery Beat task
```

### GASTEC Pult (`/pult/`)

The former Google-Sheets "GASTEC Пульт" page now runs on the platform's own data (`apps/pult`). Every `tasks.Task` gets a `TaskWorkflow` row with a sequential № and the Pult's 10-step status (Черновик → Новая → … → Принята); `Task.status` is kept in sync, so the regular task board stays correct. All transitions (issue ТЗ, propose/approve the term, submit, accept, send back) are checked on the server in `apps/pult/services.py`. KPI points, the working calendar (holidays) and task templates are edited in the Django admin under "GASTEC Пульт".

The UI lives in `static/pult/pult.js` + `templates/pult/` and is shown in an iframe so its global CSS does not touch the platform layout.

- **Состав / График проекта** — `PlanRow` (`apps/pult/plan.py`). Dates, links and the critical path are calculated in the browser; the server stores the rows, writes only projects the user may plan (admin/manager, or a GIP of the project) and rejects a save made on stale data (`PultSettings.plan_version`). The «Из объектов платформы» button copies objects, pod-objects and disciplines entered in the project wizard into the composition (once per item, tracked by `PlanRow.source_key`). Disciplines are the platform's `accounts.Discipline` plus `DisciplineConfig` (duration, typical links, cipher code); cipher rules and stages (Смета/Оформление/Печать) are in the admin.
- **Финансы / Договоры** — `apps/pult/finance.py`, visible to admin/manager/finance only. An operation is a `finance.FinancialRecord` (one per currency) plus `OperationInfo`; a contract with a platform employee is mirrored into `finance.EmployeeContract`, so the payment also shows on the Finance and "My salary" pages. The USD rate comes from Finance settings.
- Per-employee pay type (оклад/договор), weekly hours and stage role are set in the admin under "Employee settings"; an employee without settings counts as salaried.

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

`docker-compose.yml` runs the full stack: `web` (gunicorn, non-root), `celery-worker` (with embedded beat), `telegram-bot`, `db` (Postgres) with a daily `db-backup`, `redis`, `nginx` (HTTPS reverse proxy + static files) and `certbot` (Let's Encrypt renewal). Uploaded media is never served by nginx — only through Django's permission-checked `protected_media` view.

Step-by-step server setup (firewall, HTTPS certificate, `.env`) is in [RUNNING.md](RUNNING.md), section A. In short:

```bash
sudo sh deploy/server-setup.sh      # once: updates, Docker, firewall, fail2ban
cp .env.example .env && nano .env   # DOMAIN, SECRET_KEY, POSTGRES_PASSWORD, ...
docker compose build
sh deploy/init-letsencrypt.sh       # once: first HTTPS certificate
docker compose up -d
```
