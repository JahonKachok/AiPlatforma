FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=aiplatforma.settings.prod

WORKDIR /app

# build-essential kerak emas: barcha kutubxonalar (Pillow, psycopg[binary],
# pydantic-core...) tayyor manylinux wheel bilan keladi — image ~250 MB yengil.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p media staticfiles backups locale \
    && chmod +x docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "aiplatforma.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
