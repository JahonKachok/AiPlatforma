from .base import *  # noqa: F401,F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Run Celery tasks synchronously in dev/tests so `runserver`/`manage.py test`
# work without a running Redis broker + worker. Real async execution (via
# Redis + a separate worker/beat process) only happens in prod.py.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
