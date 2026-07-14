# AiPlatforma — start-dev.ps1 ochgan barcha jarayonlarni to'xtatish.
$patterns = "runserver", "run_telegram_bot", "celery"

Get-CimInstance Win32_Process -Filter "Name like 'python%.exe' or Name like 'celery%.exe'" |
    Where-Object { $cl = $_.CommandLine; $patterns | Where-Object { $cl -match $_ } } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "to'xtatildi: PID $($_.ProcessId)"
    }

Write-Host "Barcha AiPlatforma jarayonlari to'xtatildi." -ForegroundColor Cyan
