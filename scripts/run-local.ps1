# Локальный запуск backend + telegram (без Docker-образов backend/telegram).
# Инфраструктура: postgres, redis, kafka — в Docker.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Stopping Docker backend/telegram (avoid port and polling conflicts)..."
docker compose stop backend telegram 2>$null

Write-Host "Starting infrastructure..."
docker compose up -d postgres redis zookeeper kafka

$env:DATABASE_URL = "postgresql://notification_user:notification_password@127.0.0.1:5432/booking"
$env:BACKEND_URL = "http://127.0.0.1:8083"

if (Test-Path "$Root\.env") {
    Get-Content "$Root\.env" | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $val = $matches[2].Trim()
            Set-Item -Path "env:$name" -Value $val
        }
    }
}

Write-Host ""
Write-Host "=== Terminal 1: backend ==="
Write-Host "cd `"$Root\services\backend`""
Write-Host "pip install -r requirements.txt"
Write-Host "`$env:DATABASE_URL = `"$env:DATABASE_URL`""
Write-Host "python main.py"
Write-Host ""
Write-Host "=== Terminal 2: frontend (/register, /login) ==="
Write-Host ".\scripts\start-frontend.ps1"
Write-Host "# ngrok http 127.0.0.1:5173  ->  FRONTEND_URL=https://<host> in .env"
Write-Host ""
Write-Host "=== Terminal 3: telegram bot ==="
Write-Host "cd `"$Root\services\telegram-frontend`""
Write-Host "pip install -r requirements.txt"
Write-Host "`$env:BACKEND_URL = `"http://127.0.0.1:8083`""
Write-Host "`$env:TELEGRAM_BOT_TOKEN = `"<from .env>`""
Write-Host "python main.py"
Write-Host ""
Write-Host "Then send /start in Telegram. Only ONE bot instance must run."
