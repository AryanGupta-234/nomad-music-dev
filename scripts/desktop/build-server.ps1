$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot "../..")).Path
Set-Location $root
$env:NOMAD_PROJECT_ROOT = $root

Write-Host "NOMAD project root: $root" -ForegroundColor Cyan

if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Virtual environment missing. Run .\scripts\windows\setup-windows.ps1 first.' }
$py = Join-Path $root '.venv\Scripts\python.exe'
Write-Host "Installing server/PyInstaller dependencies into .venv..." -ForegroundColor Cyan
& $py -m pip install -r server/requirements.txt pyinstaller --disable-pip-version-check
if ($LASTEXITCODE -ne 0) {
    throw "Dependency installation failed with exit code $LASTEXITCODE"
}

$dist = Join-Path $root "dist"
$buildDir = Join-Path $root "build"
if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
if (Test-Path $buildDir) { Remove-Item $buildDir -Recurse -Force }

Write-Host "Building NOMAD server sidecar..." -ForegroundColor Cyan
& $py -m PyInstaller `
    --clean `
    --noconfirm `
    --distpath $dist `
    --workpath $buildDir `
    scripts/desktop/nomad-server.spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
}

$exe = Join-Path $dist "nomad-server.exe"
if (!(Test-Path $exe)) {
    throw "PyInstaller completed but expected output was not found: $exe"
}

$target = Join-Path $root "apps/desktop/src-tauri/binaries"
New-Item -ItemType Directory -Force -Path $target | Out-Null
$targetExe = Join-Path $target "nomad-server-x86_64-pc-windows-msvc.exe"
Copy-Item $exe $targetExe -Force

Write-Host "Build successful:" -ForegroundColor Green
Write-Host "  $targetExe" -ForegroundColor Green
