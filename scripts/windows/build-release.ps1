$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$root=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $root
& "$PSScriptRoot/check-prereqs.ps1"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Run scripts\windows\setup-windows.ps1 first.' }
Write-Host '1/3 Building NOMAD server sidecar...' -ForegroundColor Cyan
& "$root\scripts\desktop\build-server.ps1"; if ($LASTEXITCODE -ne 0) { throw 'Sidecar build failed.' }
$sidecar=Join-Path $root 'apps\desktop\src-tauri\binaries\nomad-server-x86_64-pc-windows-msvc.exe'
if (-not (Test-Path $sidecar)) { throw "Sidecar not found: $sidecar" }
Write-Host '2/3 Building Tauri application and NSIS installer...' -ForegroundColor Cyan
Push-Location apps\desktop; npm run build; if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Tauri release build failed.' }; Pop-Location
Write-Host '3/3 Release artifacts:' -ForegroundColor Cyan
$bundle=Join-Path $root 'apps\desktop\src-tauri\target\release\bundle'
if (Test-Path $bundle) { Get-ChildItem $bundle -Recurse -File | Where-Object {$_.Extension -in '.exe','.msi'} | Select-Object FullName,Length }
Write-Host 'Release build complete.' -ForegroundColor Green
