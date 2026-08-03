# Cloudflare Tunnel — boburovich.uz'ni shu kompyuterdagi localhost:8000'ga ulaydi.
# Avtomatik ishga tushadi: Windows Startup papkasidagi yorliq orqali (logon'da).

$cloudflared = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
& $cloudflared tunnel run buildflow
