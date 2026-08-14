# NOMAD Music — Windows Installation & Build

## End-user installation

1. Run the `NOMAD Music <version>-setup.exe` installer produced by the release build.
2. The installer installs NOMAD Music and automatically installs Microsoft Edge WebView2 when the runtime is missing.
3. Launch **NOMAD Music** from the Start Menu or desktop shortcut.
4. NOMAD starts its local FastAPI sidecar automatically and opens the React UI inside the Tauri WebView.

No Python, Node.js, Rust, or separate web browser is required for the installed end-user application.

## Developer prerequisites

Install:

- Windows 10 1803+ or Windows 11
- Python 3.11+
- Node.js LTS + npm
- Rust toolchain with MSVC target
- Visual Studio Build Tools with **Desktop development with C++**
- Git

WebView2 is checked and installed by the NOMAD setup script when missing. Tauri documents WebView2 as the Windows web runtime and Microsoft's Evergreen Bootstrapper as the normal deployment mechanism. See `WEBVIEW2.md`.

## Setup

From the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-prereqs.ps1
.\scripts\windows\setup-windows.ps1
```

The setup script creates `.venv`, installs server dependencies, installs the UI/Tauri npm dependencies, configures the Rust MSVC target, and installs WebView2 if needed.

## Development

```powershell
.\scripts\windows\dev.ps1
```

## Production installer

```powershell
.\scripts\windows\build-release.ps1
```

The primary artifact is an NSIS installer under:

```text
apps\desktop\src-tauri\target\release\bundle\nsis\
```

## API credentials

Provider credentials are optional during local development. See `docs/setup/API-CREDENTIALS.md`.

## First-run expectations

The installed app is local-first:

- SQLite database is created locally.
- Background indexing runs locally.
- Provider integrations enrich the local Track Graph when credentials are connected.
- No cloud database is required for the desktop build.
