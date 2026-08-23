from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401,F403

DEBUG = False

# .env.example dagi namuna kalit bilan ishga tushib ketmaslik uchun — u bilan
# sessiya va CSRF imzolarini istalgan odam qalbakilashtira oladi.
if SECRET_KEY == "changeme-generate-a-real-secret-key":  # noqa: F405
    raise ImproperlyConfigured(
        "SECRET_KEY hali .env.example dagi namuna qiymatida. "
        "Yangi kalit yarating: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )

STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}

# Nginx TLS'ni o'zi tugatadi va X-Forwarded-Proto ni qo'yadi. Busiz Django
# so'rovni har doim HTTP deb biladi: SECURE_SSL_REDIRECT cheksiz redirect
# halqasiga tushadi, secure cookie'lar esa hech qachon yuborilmaydi.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Sessiya cookie'siga JS tegmaydi (default), CSRF cookie'siga ham tegmasin —
# token shablonlardagi {% csrf_token %} maydonidan o'qiladi (static/js/kanban.js).
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Login urinishlarini cheklash hisoblagichi (apps/accounts/views.py) shu
# cache'da yashaydi, shuning uchun u jarayonlar orasida umumiy bo'lishi kerak:
# standart LocMemCache da har bir ishchining o'z hisoblagichi bo'lib, cheklov
# ishchilar soniga ko'payib ketadi.
#
# Redis hamma joyda ham yo'q (masalan lokal Windows o'rnatmasida broker
# `sqla+sqlite://`). Redis bo'lmaganda Redis'ga ulanishga urinsak, har bir
# login so'rovi ConnectionError bilan 500 qaytarardi — shuning uchun bu yerda
# mavjud infratuzilmaga qarab tanlaymiz.
_cache_url = env("CACHE_URL", default="")  # noqa: F405
if not _cache_url and CELERY_BROKER_URL.startswith("redis://"):  # noqa: F405
    # Broker Redis bo'lsa, o'sha serverning boshqa bazasini olamiz.
    _cache_url = CELERY_BROKER_URL.rsplit("/", 1)[0] + "/1"  # noqa: F405

if _cache_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _cache_url,
        }
    }
else:
    # Fayl asosidagi cache — Redis'siz ham jarayonlar orasida umumiy.
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
            "LOCATION": str(BASE_DIR / ".django-cache"),  # noqa: F405
        }
    }
