@echo off
setlocal
REM Vazifa rejalashtiruvchisidan yoki boshqa papkadan ishga tushirilsa ham loyiha papkasida ishlasin.
cd /d "%~dp0"

REM Python chiqishi logga darhol va UTF-8 da yozilsin.
set "PYTHONUNBUFFERED=1"
set "PYTHONIOENCODING=utf-8"

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
echo Server 3031-portda ishlayapti. Log: logs\server.log. To'xtatish: oynani yoping.

:start
echo [%date% %time%] Server ishga tushmoqda>> logs\server.log
python manage.py runserver 0.0.0.0:3031 >> logs\server.log 2>&1
echo [%date% %time%] Server to'xtadi, chiqish kodi: %errorlevel%. 5 soniyadan keyin qayta yoqiladi.>> logs\server.log
echo [%date% %time%] Server to'xtadi. Sababi: logs\server.log. 5 soniyadan keyin qayta yoqiladi.
REM timeout buyrug'i oynasiz (Task Scheduler) rejimda ishlamaydi, ping ishlaydi.
ping -n 6 127.0.0.1 >nul
goto start
