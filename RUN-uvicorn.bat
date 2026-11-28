@echo off
setlocal
REM Vazifa rejalashtiruvchisidan yoki boshqa papkadan ishga tushirilsa ham loyiha papkasida ishlasin.
cd /d "%~dp0"

REM Python chiqishi logga darhol va UTF-8 da yozilsin.
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

REM Fayl o'zini "bot" argumenti bilan fon jarayon sifatida chaqiradi:
REM bu holda faqat Telegram bot tsikli ishlaydi (venv va muhit ota jarayondan meros).
if /i "%~1"=="bot" goto bot

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

echo Server 3031-portda ishlayapti. Log: logs\server.log
echo Telegram bot ishlayapti. Log: logs\telegram_bot.log
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
