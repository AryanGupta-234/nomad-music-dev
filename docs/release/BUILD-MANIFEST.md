# NOMAD Music — Build Manifest

## Canonical Windows commands

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-prereqs.ps1
.\scripts\windows\setup-windows.ps1
.\scripts\windows\dev.ps1
.\scripts\windows\build-release.ps1
```

## Primary Windows artifact

```text
apps/desktop/src-tauri/target/release/bundle/nsis/*-setup.exe
```

## Runtime

```text
Tauri 2
React/Vite
FastAPI
SQLite
bundled Python sidecar
```

## Developer prerequisites

Python, Node.js, Rust, Visual Studio C++ Build Tools, Git and WebView2 are build-machine requirements. They are not manually launched by end users.

## Release validation

```text
[ ] prerequisite check
[ ] backend pytest suite
[ ] fresh database migration
[ ] Python compile check
[ ] frontend production build
[ ] sidecar exists
[ ] Tauri bundle succeeds
[ ] installer runs
[ ] clean installation succeeds
[ ] app starts without a terminal
[ ] uninstall does not delete user music
```
