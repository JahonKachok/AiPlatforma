@echo off
REM Django'ni ASGI (uvicorn) orqali ishga tushirish.
REM Diqqat: serverdagi asosiy o'rnatma Docker + gunicorn + nginx (RUNNING.md, A bo'lim).
REM Bu fayl faqat Windows'da ASGI'ni qo'lda sinash uchun.
call .venv\Scripts\activate.bat && uvicorn aiplatforma.asgi:application --host 0.0.0.0 --port 3031 --workers 4 --log-level info
