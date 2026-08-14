$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
Write-Host 'NOMAD Music - Windows prerequisite check' -ForegroundColor Cyan
Write-Host "Project: $root" -ForegroundColor DarkGray

function Test-Command([string]$Name) {
    return $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Show-Version([string]$Name) {
    if (Test-Command $Name) {
        try {
            $out = & $Name --version 2>$null | Select-Object -First 1
            if ($out) { return [string]$out }
        } catch {}
    }
    return '<missing>'
}

$checks = @(
    [pscustomobject]@{Name='Python'; Present=(Test-Command 'python'); Required=$true; SetupCanInstall=$false},
    [pscustomobject]@{Name='Node.js'; Present=(Test-Command 'node'); Required=$false; SetupCanInstall=$true},
    [pscustomobject]@{Name='npm'; Present=(Test-Command 'npm'); Required=$false; SetupCanInstall=$true},
    [pscustomobject]@{Name='Rust/Cargo'; Present=(Test-Command 'cargo'); Required=$false; SetupCanInstall=$true},
    [pscustomobject]@{Name='rustup'; Present=(Test-Command 'rustup'); Required=$false; SetupCanInstall=$true},
    [pscustomobject]@{Name='Git'; Present=(Test-Command 'git'); Required=$false; SetupCanInstall=$true}
)

foreach ($c in $checks) {
    $mark = if ($c.Present) { 'OK ' } elseif ($c.SetupCanInstall) { 'MISS' } else { 'MISS' }
    $color = if ($c.Present) { 'Green' } elseif ($c.SetupCanInstall) { 'Yellow' } else { 'Red' }
    Write-Host ("[{0}] {1}  {2}" -f $mark,$c.Name,(Show-Version $c.Name.Split('/')[0])) -ForegroundColor $color
}

$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$hasVS = Test-Path $vswhere
Write-Host ("[{0}] Microsoft C++ Build Tools" -f ($(if ($hasVS) {'OK '} else {'MISS'}))) -ForegroundColor ($(if ($hasVS) {'Green'} else {'Red'}))

& "$PSScriptRoot/check-webview2.ps1"
$hasWebView2 = ($LASTEXITCODE -eq 0)

$hardMissing = @($checks | Where-Object { -not $_.Present -and $_.Required })
if (-not $hasVS) { $hardMissing += [pscustomobject]@{Name='Microsoft C++ Build Tools'} }

if ($hardMissing.Count -gt 0) {
    Write-Host ''
    Write-Host 'Required prerequisites are missing.' -ForegroundColor Red
    Write-Host 'Run setup-windows.ps1 to install supported developer prerequisites automatically where possible.' -ForegroundColor Yellow
    exit 2
}

if (-not $hasWebView2) {
    Write-Host 'WebView2 is missing; setup-windows.ps1 will install it automatically.' -ForegroundColor Yellow
}

Write-Host 'Prerequisite check passed (installable developer prerequisites may still be missing).' -ForegroundColor Green
exit 0
