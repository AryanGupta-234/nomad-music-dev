$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $root
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Run setup-windows.ps1 first.' }
$env:PYTHONPATH=(Join-Path $root 'server')
Write-Host 'Starting NOMAD Music local backend on http://127.0.0.1:8765' -ForegroundColor Cyan
Push-Location server
try {
  & '..\.venv\Scripts\python.exe' '-m' 'uvicorn' 'app.main:app' '--host' '127.0.0.1' '--port' '8765'
} finally { Pop-Location }
