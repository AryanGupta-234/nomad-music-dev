$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $root

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
  Write-Host ''
  Write-Host 'NOMAD Music Python environment is missing.' -ForegroundColor Yellow
  Write-Host 'Run this once from the repository root:' -ForegroundColor Cyan
  Write-Host '  .\scripts\windows\setup-windows.ps1' -ForegroundColor White
  Write-Host ''
  Write-Host 'If setup already completed in another PowerShell window, restart PowerShell so PATH changes are loaded, then rerun setup if .venv is still missing.' -ForegroundColor DarkYellow
  throw 'NOMAD backend prerequisites are not installed. Run setup-windows.ps1 first.'
}

$env:PYTHONPATH=(Join-Path $root 'server')
# 8765 is the canonical local desktop API port. Explicitly override any stale
# PUBLIC_BASE_URL from .env so OAuth callbacks match the process actually running.
$env:PUBLIC_BASE_URL='http://127.0.0.1:8765'
Write-Host 'Starting NOMAD Music local backend on http://127.0.0.1:8765' -ForegroundColor Cyan
Write-Host 'OAuth callback base: http://127.0.0.1:8765' -ForegroundColor DarkGray
Push-Location server
try {
  & $python '-m' 'uvicorn' 'app.main:app' '--host' '127.0.0.1' '--port' '8765'
} finally { Pop-Location }
