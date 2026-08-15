$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$server = Join-Path $repo 'server'
$python = Join-Path $repo '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    throw 'NOMAD virtual environment not found. Run .\scripts\windows\setup-windows.ps1 first.'
}

Push-Location $server
try {
    & $python -m app.tools.doctor_v4
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
