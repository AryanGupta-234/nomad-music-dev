$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $root

function Require-Command([string]$Name, [string]$Hint) {
    if ($null -eq (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is not available on PATH. $Hint"
    }
}

Require-Command 'python' 'Run scripts\\windows\\setup-windows.ps1 first.'
Require-Command 'node' 'Install Node.js LTS and reopen PowerShell.'
Require-Command 'npm' 'Install Node.js LTS and reopen PowerShell.'

if (-not (Test-Path '.venv\Scripts\python.exe')) {
    throw 'Python venv is missing. Run scripts\\windows\\setup-windows.ps1 first.'
}

$desktop = Join-Path $root 'apps\desktop'
$ui = Join-Path $desktop 'ui'
$tauriCmd = Join-Path $desktop 'node_modules\.bin\tauri.cmd'
$tauriLib = Join-Path $desktop 'src-tauri\src\lib.rs'
$uiNodeModules = Join-Path $ui 'node_modules'

# Make dev.ps1 resilient even when setup-windows.ps1 was skipped or partially
# completed. Tauri CLI lives in the desktop package's local node_modules.
if (-not (Test-Path $tauriLib)) {
    throw 'Tauri source is incomplete: apps/desktop/src-tauri/src/lib.rs is missing. Re-extract the current Stable v2 package.'
}

if (-not (Test-Path $tauriCmd)) {
    Write-Host 'Tauri CLI is not installed in apps/desktop. Installing npm dependencies...' -ForegroundColor Yellow
    Push-Location $desktop
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed in apps/desktop (exit $LASTEXITCODE)." }
    }
    finally { Pop-Location }
}

if (-not (Test-Path $tauriCmd)) {
    throw 'Tauri CLI is still missing after npm install. Check apps/desktop/package.json and npm output.'
}

if (-not (Test-Path $uiNodeModules)) {
    Write-Host 'Desktop UI dependencies are missing. Installing...' -ForegroundColor Yellow
    Push-Location $ui
    try {
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed in apps/desktop/ui (exit $LASTEXITCODE)." }
    }
    finally { Pop-Location }
}

$env:PYTHONPATH=(Join-Path $root 'server')
# 8765 is the canonical local desktop API port. Explicitly override any stale
# PUBLIC_BASE_URL from .env so OAuth callbacks match the backend process.
$env:PUBLIC_BASE_URL='http://127.0.0.1:8765'
$api=Start-Process -FilePath (Join-Path $root '.venv\Scripts\python.exe') -ArgumentList '-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8765' -WorkingDirectory (Join-Path $root 'server') -PassThru
try {
    Write-Host 'Waiting for NOMAD local backend on http://127.0.0.1:8765...' -ForegroundColor DarkGray
    $ready = $false
    for ($i=0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 250
        try {
            $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8765/api/v1/health' -TimeoutSec 2
            if ($r.StatusCode -eq 200) { $ready = $true; break }
        } catch {}
        if ($api.HasExited) { throw "NOMAD backend exited before becoming ready (exit $($api.ExitCode))." }
    }
    if (-not $ready) { throw 'NOMAD backend did not become ready on http://127.0.0.1:8765.' }

    Push-Location $desktop
    try {
        # Invoke the local CLI explicitly; do not rely on a globally installed `tauri` command.
        & $tauriCmd dev
        if ($LASTEXITCODE -ne 0) { throw 'Tauri dev failed.' }
    }
    finally { Pop-Location }
}
finally {
    if ($api -and -not $api.HasExited) { Stop-Process -Id $api.Id -Force -ErrorAction SilentlyContinue }
}
