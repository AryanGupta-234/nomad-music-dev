$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-WebView2Version {
    $ids = @(
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
        'HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}',
        'HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}'
    )
    foreach ($key in $ids) {
        try {
            $v = (Get-ItemProperty -Path $key -Name pv -ErrorAction Stop).pv
            if ($v) { return [string]$v }
        } catch {}
    }
    return $null
}

$v = Get-WebView2Version
if ($v) {
    Write-Host "WebView2 Runtime: $v" -ForegroundColor Green
    exit 0
}

$paths = @(
    "$env:ProgramFiles(x86)\Microsoft\EdgeWebView\Application",
    "$env:ProgramFiles\Microsoft\EdgeWebView\Application",
    "$env:LOCALAPPDATA\Microsoft\EdgeWebView\Application"
)
foreach ($root in $paths) {
    if (Test-Path $root) {
        $versions = @(Get-ChildItem $root -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^\d+\.\d+\.\d+\.\d+$' } | Sort-Object Name -Descending)
        if ($versions.Count -gt 0) {
            Write-Host "WebView2 Runtime: $($versions[0].Name)" -ForegroundColor Green
            exit 0
        }
    }
}

Write-Host 'WebView2 Runtime: NOT FOUND' -ForegroundColor Yellow
exit 1
