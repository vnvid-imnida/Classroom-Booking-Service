# Запуск FastAPI backend на хосте (рекомендуется для разработки бота).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

docker compose stop backend telegram 2>$null

$env:DATABASE_URL = "postgresql://notification_user:notification_password@127.0.0.1:5432/booking"
Set-Location "$Root\services\backend"

Write-Host "Starting backend on http://127.0.0.1:8083 ..."
python main.py
