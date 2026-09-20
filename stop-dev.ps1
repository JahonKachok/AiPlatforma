# BuildFlow — start-dev.ps1 / start-prod.ps1 ochgan barcha jarayonlarni to'xtatish.
$patterns = "runserver", "serve_prod", "waitress", "run_telegram_bot", "celery"

# Faqat shu loyiha papkasidagi jarayonlar: kompyuterda boshqa loyihalar
# (masalan, Orderbot) ham celery/runserver ishlatishi mumkin.
$root = [regex]::Escape($PSScriptRoot)

Get-CimInstance Win32_Process -Filter "Name like 'python%.exe' or Name like 'celery%.exe'" |
    Where-Object { $cl = $_.CommandLine; ($cl -match $root) -and ($patterns | Where-Object { $cl -match $_ }) } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "to'xtatildi: PID $($_.ProcessId)"
    }

Write-Host "Barcha BuildFlow jarayonlari to'xtatildi." -ForegroundColor Cyan
