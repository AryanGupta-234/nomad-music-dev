$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Set-Location $root

function Test-Command([string]$Name) { return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue) }
function Install-WingetPackage([string]$Id, [string]$DisplayName) {
    if (-not (Test-Command 'winget')) { throw "winget is required to auto-install $DisplayName. Install it from Microsoft App Installer, then rerun setup." }
    Write-Host "Installing $DisplayName via winget..." -ForegroundColor Cyan
    & winget install --id $Id --exact --silent --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "$DisplayName installation failed with exit code $LASTEXITCODE." }
}

Write-Host 'NOMAD Music - Windows setup' -ForegroundColor Cyan
& "$PSScriptRoot/check-prereqs.ps1"

# Developer dependencies: install only when missing.
if (-not (Test-Command 'node')) { Install-WingetPackage 'OpenJS.NodeJS.LTS' 'Node.js LTS' }
if (-not (Test-Command 'git'))  { Install-WingetPackage 'Git.Git' 'Git' }

# Refresh PATH from machine/user scopes after installer changes.
$env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')

if (-not (Test-Command 'rustup')) {
    Install-WingetPackage 'Rustlang.Rustup' 'rustup'
    $env:Path = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
}

Write-Host 'Installing/configuring Rust MSVC toolchain...' -ForegroundColor Cyan
& rustup toolchain install stable-x86_64-pc-windows-msvc
if ($LASTEXITCODE -ne 0) { throw 'Rust MSVC toolchain installation failed.' }
& rustup default stable-msvc
if ($LASTEXITCODE -ne 0) { throw 'Rust stable-msvc selection failed.' }
& rustup target add x86_64-pc-windows-msvc
if ($LASTEXITCODE -ne 0) { throw 'Rust MSVC target setup failed.' }

# WebView2 is handled even though it is not a developer prerequisite for source compilation.
& "$PSScriptRoot/install-webview2.ps1"
if ($LASTEXITCODE -ne 0) { throw 'WebView2 Runtime setup failed.' }

if (-not (Test-Path '.venv\Scripts\python.exe')) { python -m venv .venv }
Write-Host 'Installing Python dependencies...' -ForegroundColor Cyan
& .\.venv\Scripts\python.exe -m pip install -r server\requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies failed.' }

Write-Host 'Installing desktop UI dependencies...' -ForegroundColor Cyan
Push-Location apps\desktop\ui
npm install
if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'UI npm install failed.' }
Pop-Location

Push-Location apps\desktop
npm install
if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Tauri npm install failed.' }
Pop-Location

Write-Host 'NOMAD Music Windows setup complete.' -ForegroundColor Green
Write-Host 'Restart PowerShell if Windows installed Node/Git/Rust during this run.' -ForegroundColor Yellow
