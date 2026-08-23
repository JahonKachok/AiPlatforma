# BuildFlow — lokal kompyuterda PRODUCTION rejimida ishga tushirish.
#
# start-dev.ps1 dan farqi:
#   * DJANGO_SETTINGS_MODULE = aiplatforma.settings.prod  -> DEBUG=False,
#     HSTS, secure cookie'lar, SECURE_PROXY_SSL_HEADER, SECRET_KEY tekshiruvi.
#   * runserver o'rniga waitress (Django'ning dev serveri ommaviy domen uchun
#     mo'ljallanmagan; Windows'da gunicorn ishlamaydi).
#   * Statik fayllar whitenoise orqali staticfiles/ dan beriladi.
#
# Foydalanish:  .\start-prod.ps1        To'xtatish: .\stop-dev.ps1

$ErrorActionPreference = "Stop"

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$celery = Join-Path $PSScriptRoot ".venv\Scripts\celery.exe"
$env:DJANGO_SETTINGS_MODULE = "aiplatforma.settings.prod"

Write-Host "BuildFlow (PRODUCTION) ishga tushmoqda..." -ForegroundColor Cyan

# Migratsiya + statik fayllar. input.css - Tailwind manba fayli, tarqatilmaydi.
& $python manage.py migrate --noinput
if ($LASTEXITCODE -ne 0) { throw "migrate xato bilan tugadi" }
& $python manage.py collectstatic --noinput --ignore=input.css | Out-Null
if ($LASTEXITCODE -ne 0) { throw "collectstatic xato bilan tugadi" }
Write-Host "  [0/4] migrate + collectstatic -> tayyor" -ForegroundColor Green

# Waitress faqat localhost'da tinglaydi: tashqi dunyoga Cloudflare Tunnel
# chiqaradi, shuning uchun portni butun tarmoqqa ochish shart emas.
Start-Process -FilePath $python -ArgumentList "serve_prod.py" `
    -WorkingDirectory $PSScriptRoot -WindowStyle Minimized
Write-Host "  [1/4] Waitress (WSGI)   -> http://127.0.0.1:8000" -ForegroundColor Green

Start-Process -FilePath $python -ArgumentList "manage.py", "run_telegram_bot" `
    -WorkingDirectory $PSScriptRoot -WindowStyle Minimized
Write-Host "  [2/4] Telegram bot      -> long polling" -ForegroundColor Green

Start-Process -FilePath $celery -ArgumentList "-A", "aiplatforma", "worker", "--pool=solo", "-l", "info" `
    -WorkingDirectory $PSScriptRoot -WindowStyle Minimized
Write-Host "  [3/4] Celery worker     -> fon vazifalari" -ForegroundColor Green

Start-Process -FilePath $celery -ArgumentList "-A", "aiplatforma", "beat", "-l", "info" `
    -WorkingDirectory $PSScriptRoot -WindowStyle Minimized
Write-Host "  [4/4] Celery beat       -> kunlik AI hisobot (08:00)" -ForegroundColor Green

Write-Host ""
Write-Host "Tayyor. DEBUG=False, statik fayllar whitenoise orqali." -ForegroundColor Cyan
Write-Host "Domen uchun Cloudflare Tunnel ham kerak:  .\start-tunnel.ps1" -ForegroundColor Yellow
