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

# Tarjimalar (.po -> .mo) build vaqtida kompilyatsiya qilinadi, shunda
# repodagi .mo eskirgan bo'lsa ham yangi matnlar tarjimasiz qolmaydi.
# gettext faqat shu qadam uchun o'rnatiladi va darhol olib tashlanadi.
# SECRET_KEY bu yerda faqat Django'ni yuklash uchun — image'da qolmaydi.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && SECRET_KEY=build-only DJANGO_SETTINGS_MODULE=aiplatforma.settings.dev \
       python manage.py compilemessages \
    && find locale -name '*.po' -delete \
    && apt-get purge -y gettext && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Ilova root huquqisiz ishlaydi: kodda zaiflik topilsa ham, hujumchi
# konteyner ichida root bo'lmaydi va kodni o'zgartira olmaydi (kod root'ga
# tegishli, ilova faqat media/staticfiles/backups ga yoza oladi).
RUN useradd --system --uid 1000 --no-create-home --home-dir /app app \
    && mkdir -p media staticfiles backups \
    && chown app:app media staticfiles backups \
    && chmod +x docker-entrypoint.sh
USER app

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["gunicorn", "aiplatforma.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
