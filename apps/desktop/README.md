# NOMAD Music Desktop

NOMAD Music is a desktop `.exe` application built with Tauri 2 and a React/Vite WebView.

## Runtime model

- Tauri owns the desktop window/lifecycle.
- The WebView renders the Music UI.
- In production the Tauri shell launches the bundled `nomad-server` sidecar.
- The sidecar exposes the local FastAPI API at `http://127.0.0.1:8765`.
- The WebView talks only to the local NOMAD API; provider credentials/business logic stay in the backend.

## Development

Run the API separately:

```text
uvicorn app.main:app --reload --host 127.0.0.1 --port 8765
```

Then run the desktop UI/Tauri dev command once Rust/Tauri tooling is installed.

## Build

Windows developers should use the repository-level scripts rather than invoking PyInstaller/Tauri manually:

```powershell
.\scripts\windows\setup-windows.ps1
.\scripts\windows\dev.ps1
.\scripts\windows\build-release.ps1
```
