$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $root

Write-Host 'NOMAD Music Stable Testing v2 - verification' -ForegroundColor Cyan

if (-not (Test-Path '.venv\Scripts\python.exe')) {
  throw 'Python venv not found. Run scripts\windows\setup-windows.ps1 first.'
}

$env:PYTHONPATH=(Join-Path $root 'server')
& '.\.venv\Scripts\python.exe' '-m' 'pytest' '-q' 'server/tests'
if ($LASTEXITCODE -ne 0) { throw 'Backend test suite failed.' }

Write-Host ''
Write-Host 'Stable verification passed.' -ForegroundColor Green
Write-Host 'Next: build the Windows sidecar/installer with scripts\windows\build-release.ps1' -ForegroundColor Yellow
