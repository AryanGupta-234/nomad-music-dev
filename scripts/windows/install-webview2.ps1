$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$installer = Join-Path $env:TEMP 'NOMAD-WebView2-Bootstrapper.exe'
$url = 'https://go.microsoft.com/fwlink/p/?LinkId=2124703'

Write-Host 'Checking Microsoft Edge WebView2 Runtime...' -ForegroundColor Cyan
& "$PSScriptRoot/check-webview2.ps1"
if ($LASTEXITCODE -eq 0) {
    Write-Host 'WebView2 Runtime is already installed.' -ForegroundColor Green
    exit 0
}

Write-Host 'Downloading the official Microsoft Evergreen WebView2 Bootstrapper...' -ForegroundColor Cyan
Invoke-WebRequest -Uri $url -OutFile $installer -UseBasicParsing

Write-Host 'Installing WebView2 Runtime silently...' -ForegroundColor Cyan
$p = Start-Process -FilePath $installer -ArgumentList '/silent','/install' -Wait -PassThru
Remove-Item $installer -Force -ErrorAction SilentlyContinue

if ($p.ExitCode -ne 0) {
    throw "WebView2 installation failed with exit code $($p.ExitCode)."
}

& "$PSScriptRoot/check-webview2.ps1"
if ($LASTEXITCODE -ne 0) {
    throw 'WebView2 installer completed, but the runtime could not be detected afterward.'
}

Write-Host 'WebView2 Runtime installation complete.' -ForegroundColor Green
