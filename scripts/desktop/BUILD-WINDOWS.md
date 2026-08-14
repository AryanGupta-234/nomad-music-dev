# NOMAD Music Windows sidecar build

From the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\desktop\build-server.ps1
```

The script injects `NOMAD_PROJECT_ROOT` because PyInstaller spec files are executed in a namespace where `__file__` is not guaranteed.

The script also checks native command exit codes explicitly, so a failed PyInstaller build cannot fall through into a misleading `Copy-Item` error.

Expected output:

```text
apps\desktop\src-tauri\binaries\nomad-server-x86_64-pc-windows-msvc.exe
```
