# Запуск Vite dev-сервера (SPA: /register, /login).
# Туннель (Windows): ngrok http 127.0.0.1:5173 — не localhost (избегает IPv6 [::1]).
# → FRONTEND_URL=https://<subdomain>.ngrok-free.dev

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Frontend = Join-Path $Root "services\frontend"

Set-Location $Frontend

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created services/frontend/.env from .env.example"
}

Write-Host "Starting Vite on http://127.0.0.1:5173 (SPA: /login, /register) ..."
Write-Host "Health: curl http://127.0.0.1:5173/__health"
Write-Host "ngrok:  ngrok http 127.0.0.1:5173   # not 'localhost' on Windows"
Write-Host "Then set in repo .env: FRONTEND_URL=https://<ngrok-host>"
Write-Host ""
Write-Host "Troubleshooting:"
Write-Host "  - ERR_NGROK_8012 / connectex forbidden: use 127.0.0.1, not localhost"
Write-Host "  - Port blocked: netstat -ano | findstr :5173"
Write-Host "    netsh interface ipv4 show excludedportrange protocol=tcp"
Write-Host "  - If 5173 excluded: set port 3000 in vite.config.ts, then ngrok http 127.0.0.1:3000"
npm run dev
