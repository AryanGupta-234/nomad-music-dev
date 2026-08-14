# NOMAD Music

**Stable Testing v2 — 2.0.0-stable-test**

NOMAD Music is a local-first unified music intelligence desktop application.

## Desktop model

The product is a single Windows `.exe` built with **Tauri 2 + React/Vite**.
The EXE owns the WebView and, in production, starts a bundled FastAPI/Python sidecar.
Users do not need to manually start Python, Node, or a browser.

```text
NOMAD Music.exe
  ├── Tauri desktop shell
  ├── React/Vite WebView
  └── bundled NOMAD FastAPI sidecar
       ├── SQLite
       ├── background worker
       ├── provider adapters
       ├── Track Graph
       ├── recommendations
       ├── lyrics
       └── AI orchestration
```

## Development

Run the backend from `server/` on `127.0.0.1:8765`, then run the Tauri desktop app from `apps/desktop`.

## Production build

1. Build the Python sidecar with `scripts/desktop/build-server.ps1` on Windows.
2. Install the Tauri CLI and Rust toolchain.
3. Run `npm run build` from `apps/desktop`.

Provider credentials remain server-side. Spotify/YouTube OAuth is handled through the local backend rather than exposing client secrets to the WebView.

## Windows quick start

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-prereqs.ps1
.\scripts\windows\setup-windows.ps1
.\scripts\windows\dev.ps1
```

Build the installer:

```powershell
.\scripts\windows\build-release.ps1
```

Stable testing guide: `STABLE_TESTING_V2.md`.

API setup: `API_SETUP.md`.

Full one-file setup: `NOMAD-Music-Stable-v2-ONE-FILE-SETUP.md`.

Full developer/release instructions: `docs/setup/INSTALLATION.md`.

## Windows desktop build

NOMAD Music is distributed as a Tauri desktop app. The NSIS installer is configured to install Microsoft Edge WebView2 automatically when it is missing; users do not need to manually install WebView2 before installing NOMAD Music.

Developer setup:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-prereqs.ps1
.\scripts\windows\setup-windows.ps1
.\scripts\windows\dev.ps1
```

Release build:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\build-release.ps1
```

See `docs/setup/INSTALLATION.md` and `docs/setup/WEBVIEW2.md` for the complete Windows flow.
