# BuildFlow — lokal development'da hammasini birga ishga tushirish.
# Foydalanish:  .\start-dev.ps1
# To'xtatish: ochilgan oynalarni yoping yoki .\stop-dev.ps1

$python = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$celery = Join-Path $PSScriptRoot ".venv\Scripts\celery.exe"

Write-Host "BuildFlow ishga tushmoqda..." -ForegroundColor Cyan

Start-Process -FilePath $python -ArgumentList "manage.py", "runserver", "8000" `
    -WorkingDirectory $PSScriptRoot -WindowStyle Minimized
Write-Host "  [1/4] Django server     -> http://localhost:8000" -ForegroundColor Green

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
Write-Host "Tayyor! Sayt: http://localhost:8000" -ForegroundColor Cyan
Write-Host "Jarayonlar minimallashtirilgan oynalarda ishlayapti."
