# NOMAD Music — Windows release checklist

## Before build

```text
[ ] Windows 10/11 x64
[ ] Git
[ ] Python 3.11+
[ ] Node.js LTS
[ ] Rust stable-msvc
[ ] x86_64-pc-windows-msvc target
[ ] Visual Studio C++ Build Tools
[ ] WebView2
[ ] .env configured as needed
```

## Commands

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-prereqs.ps1
.\scripts\windows\setup-windows.ps1
.\scripts\windows\build-release.ps1
```

## Artifacts

Primary:

```text
apps\desktop\src-tauri\target\release\bundle\nsis\*-setup.exe
```

Optional MSI can be enabled separately.
