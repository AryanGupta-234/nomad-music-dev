$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "../..")
Set-Location $root

Write-Host "Starting NOMAD Music API on 127.0.0.1:8765..." -ForegroundColor Cyan
$env:PYTHONPATH = Join-Path $root "server"
Start-Process powershell -ArgumentList @(
    "-NoProfile", "-Command",
    "`$env:PYTHONPATH='$($env:PYTHONPATH)'; Set-Location '$root/server'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload"
)

Set-Location (Join-Path $root "apps/desktop")
npm run dev
