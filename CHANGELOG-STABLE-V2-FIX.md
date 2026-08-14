# Stable v2 Fixes

## Windows dev launcher
- `scripts/windows/dev.ps1` now bootstraps missing npm dependencies before launching Tauri.
- Uses the project-local `apps/desktop/node_modules/.bin/tauri.cmd` instead of requiring a global `tauri` command.
- Waits for the local FastAPI backend health endpoint before launching the WebView.

## Spotify provider status
- Stable v2 now reports Spotify as configured when `SPOTIFY_CLIENT_ID` exists, because the desktop OAuth flow uses PKCE and does not require a client secret.
- Provider status explicitly reports `pkce`, `playback`, and whether a legacy client secret is present.
