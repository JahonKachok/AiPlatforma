"""Windows uchun production WSGI serveri (waitress).

Nega kerak:
  * gunicorn Windows'da ishlamaydi (fcntl moduli yo'q);
  * `manage.py runserver` — development serveri, ommaviy domenga chiqarish
    uchun mo'ljallanmagan;
  * waitress 2.0+ ishonchsiz manbadan kelgan `X-Forwarded-*` sarlavhalarini
    o'chirib tashlaydi. Oldida localhost'dagi reverse proxy (HTTPS'ni
    tugatuvchi) bo'lsa, u asl sxemani (https) shu sarlavhada uzatadi —
    shuning uchun faqat localhost'dan kelgan proksiga ishonamiz. Tashqi
    ulanishlar bu portga kelmaydi (faqat 127.0.0.1 tinglanadi).

Ishga tushirish:
    python serve_prod.py
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aiplatforma.settings.prod")

from waitress import serve  # noqa: E402

from aiplatforma.wsgi import application  # noqa: E402

if __name__ == "__main__":
    serve(
        application,
        host="127.0.0.1",
        port=8000,
        threads=8,
        # Faqat localhost'dagi reverse proxy'ga ishonamiz.
        trusted_proxy="127.0.0.1",
        trusted_proxy_count=1,
        trusted_proxy_headers={"x-forwarded-proto", "x-forwarded-for"},
        # Boshqa manbadan kelgan X-Forwarded-* sarlavhalari o'chiriladi.
        clear_untrusted_proxy_headers=True,
        ident="BuildFlow",
    )
