@echo off
setlocal
REM Vazifa rejalashtiruvchisidan yoki boshqa papkadan ishga tushirilsa ham loyiha papkasida ishlasin.
cd /d "%~dp0"

REM Python chiqishi logga darhol va UTF-8 da yozilsin.
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

REM Fayl o'zini "bot" yoki "beat" argumenti bilan fon jarayon sifatida chaqiradi:
REM bu holda faqat o'sha tsikl ishlaydi (venv va muhit ota jarayondan meros).
if /i "%~1"=="bot" goto bot
if /i "%~1"=="beat" goto beat

if exist "env\Scripts\activate.bat" (
    set "VENV=env"
) else if exist ".venv\Scripts\activate.bat" (
    set "VENV=.venv"
) else (
    echo XATO: virtual muhit topilmadi: env yoki .venv papkasi yo'q.
    pause
    exit /b 1
)
call "%VENV%\Scripts\activate.bat"

if not exist logs mkdir logs

REM Telegram bot shu oynaning o'zida fon jarayon bo'lib ishlaydi (start /b):
REM alohida oyna ochilmaydi, oyna yopilsa bot ham server bilan birga to'xtaydi.
start "" /b cmd /c call "%~f0" bot

REM Celery Beat: jadval bo'yicha eslatmalar (Pult 08:30/10:00/17:30, muddatlar va h.k.).
REM Dev sozlamalarida CELERY_TASK_ALWAYS_EAGER=True: beat vazifani shu jarayonning
REM o'zida bajaradi, shuning uchun alohida Celery worker kerak emas.
start "" /b cmd /c call "%~f0" beat

echo Server 3031-portda ishlayapti. Log: logs\server.log
echo Telegram bot ishlayapti. Log: logs\telegram_bot.log
echo Celery Beat ishlayapti. Log: logs\celery_beat.log
echo To'xtatish: oynani yoping.

:start
echo [%date% %time%] Server ishga tushmoqda>> logs\server.log
python manage.py runserver 0.0.0.0:3031 >> logs\server.log 2>&1
echo [%date% %time%] Server to'xtadi, chiqish kodi: %errorlevel%. 5 soniyadan keyin qayta yoqiladi.>> logs\server.log
echo [%date% %time%] Server to'xtadi. Sababi: logs\server.log. 5 soniyadan keyin qayta yoqiladi.
REM timeout buyrug'i oynasiz (Task Scheduler) rejimda ishlamaydi, ping ishlaydi.
ping -n 6 127.0.0.1 >nul
goto start

:bot
REM Bot yiqilsa (tarmoq uzilishi, xato) 10 soniyadan keyin qayta yoqiladi.
REM Token kiritilmagan bo'lsa bot o'zi kutib turadi (admin panel -> Integratsiyalar).
echo [%date% %time%] Telegram bot ishga tushmoqda>> logs\telegram_bot.log
python manage.py run_telegram_bot >> logs\telegram_bot.log 2>&1
echo [%date% %time%] Telegram bot to'xtadi, chiqish kodi: %errorlevel%. 10 soniyadan keyin qayta yoqiladi.>> logs\telegram_bot.log
echo [%date% %time%] Telegram bot to'xtadi. Sababi: logs\telegram_bot.log
ping -n 11 127.0.0.1 >nul
goto bot

:beat
REM Jadvaldagi vazifalarni bazada ro'yxatdan o'tkazish (idempotent, har startda xavfsiz).
echo [%date% %time%] Jadval vazifalari ro'yxatdan o'tkazilmoqda>> logs\celery_beat.log
python manage.py setup_periodic_tasks >> logs\celery_beat.log 2>&1
python manage.py setup_ai_periodic_tasks >> logs\celery_beat.log 2>&1
python manage.py setup_pult_periodic_tasks >> logs\celery_beat.log 2>&1
:beat_loop
echo [%date% %time%] Celery Beat ishga tushmoqda>> logs\celery_beat.log
python -m celery -A aiplatforma beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler >> logs\celery_beat.log 2>&1
echo [%date% %time%] Celery Beat to'xtadi, chiqish kodi: %errorlevel%. 10 soniyadan keyin qayta yoqiladi.>> logs\celery_beat.log
echo [%date% %time%] Celery Beat to'xtadi. Sababi: logs\celery_beat.log
ping -n 11 127.0.0.1 >nul
goto beat_loop
