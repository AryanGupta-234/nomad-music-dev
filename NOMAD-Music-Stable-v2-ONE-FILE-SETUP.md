# NOMAD Music — Stable Testing v2 — One-File Setup

## Goal

Run the complete NOMAD Music desktop application locally on Windows:

```text
NOMAD Music.exe
  ├── Tauri 2 desktop shell
  ├── WebView2
  ├── React/Vite UI
  └── local FastAPI + SQLite sidecar
```

No cloud server, Firebase, Cloudflare, OCI, or remote worker is required.

## 1. Developer prerequisites

Install:

- Windows 10/11
- Python 3.11+
- Node.js LTS
- npm
- Git
- Rustup + stable MSVC Rust toolchain
- Microsoft Visual C++ Build Tools
- WebView2 (the end-user installer installs WebView2 automatically when missing)

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-prereqs.ps1
.\scripts\windows\setup-windows.ps1
```

## 2. Local environment

Copy `.env.example` to `.env`.

Minimum:

```env
APP_ENV=development
APP_SECRET_KEY=change-me
PUBLIC_BASE_URL=http://127.0.0.1:8765
DATABASE_URL=sqlite:///./data/nomad.db
```

## 3. Spotify — current 2026 setup

Create a Spotify Development Mode app. New Development Mode apps require the owner to have Premium and are limited to one Client ID per developer and five users.

For the Windows desktop app select **Web Playback SDK**. Android, iOS and Ads API are not required for Stable v2 desktop testing. If the dashboard shows the Web API option disabled, do not treat that checkbox as a blocker; NOMAD uses the current Web API endpoints that remain available to the Development Mode app.

Set:

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
```

Stable v2 uses PKCE for the local desktop authorization flow. The client secret can remain blank for the PKCE exchange; keep it configured if your setup uses it for token refresh.

Register exactly:

```text
http://127.0.0.1:8765/api/v1/integrations/spotify/callback
```

Use `127.0.0.1`, not `localhost`.

Stable v2 uses:

```text
GET /me
GET /me/tracks
GET /me/playlists
GET /playlists/{id}/items
GET /tracks/{id}
GET /albums/{id}
GET /artists/{id}
GET /search
GET /me/top/{type}
GET /me/player/recently-played
GET /me/player
GET /me/player/queue
PUT /me/library
DELETE /me/library
GET /me/library/contains
```

Spotify changed playlist item routes from `/tracks` to `/items`, reduced search `limit` to 10, removed several batch/browse endpoints, and added generic `/me/library` operations in the 2026 Development Mode migration. Stable v2 is updated accordingly.

## 4. YouTube

Create a Google Cloud project and enable **YouTube Data API v3**. Create OAuth credentials.

Set:

```env
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_API_KEY=
```

Register:

```text
http://127.0.0.1:8765/api/v1/integrations/youtube/callback
```

## 5. Optional providers

```env
GROQ_API_KEY=
GROQ_MODEL=
LASTFM_API_KEY=
GENIUS_API_KEY=
ACOUSTID_API_KEY=
```

Keyless/current boundaries:

```text
LRCLIB
MusicBrainz
Deezer
Apple/iTunes
Audius
```

## 6. Start local backend

```powershell
.\scripts\windows\run-local-backend.ps1
```

Check:

```text
http://127.0.0.1:8765/api/v1/health
http://127.0.0.1:8765/api/v1/health/providers
```

## 7. Run the desktop development app

```powershell
.\scripts\windows\dev.ps1
```

## 8. Build the final Windows installer

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\build-release.ps1
```

Primary output:

```text
apps\desktop\src-tauri\target\release\bundle\nsis\*-setup.exe
```

WebView2 is configured through Tauri's Evergreen bootstrapper and is installed automatically by the installer if missing.

## 9. First-run test order

1. Start NOMAD Music.
2. Index a local music folder.
3. Play a local track.
4. Test queue, shuffle, repeat and persistence.
5. Open lyrics and test sync/offset.
6. Connect Spotify.
7. Sync Spotify saved tracks/playlists.
8. Test Spotify Web Playback with a Premium account.
9. Connect YouTube.
10. Sync YouTube playlists.
11. Search Spotify + YouTube + local tracks.
12. Test canonical matching.
13. Test recommendations.
14. Test Smart Queue.
15. Test Smart Radio.
16. Test Vibe Journey.
17. Configure Groq and test AI actions.
18. Restart NOMAD and verify the local database survives.

## 10. Troubleshooting

### Spotify callback fails

Confirm the callback is exactly:

```text
http://127.0.0.1:8765/api/v1/integrations/spotify/callback
```

### Spotify search returns an error

Stable v2 caps Spotify search requests at 10 results per request because the current Development Mode maximum is 10. NOMAD paginates/limits accordingly.

### Spotify playback unavailable

The Web Playback SDK requires an eligible Spotify account and playback permissions; test with the Premium account that owns the Development Mode app.

### WebView2 missing

The end-user NSIS installer is configured to bootstrap Evergreen WebView2 automatically. Developers can also run:

```powershell
.\scripts\windows\install-webview2.ps1
```

## 11. Official references

Spotify Development Mode migration:
https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide

Spotify February 2026 changelog:
https://developer.spotify.com/documentation/web-api/references/changes/february-2026

Spotify Web Playback SDK:
https://developer.spotify.com/documentation/web-playback-sdk/reference

Spotify library save:
https://developer.spotify.com/documentation/web-api/reference/save-library-items

Spotify library remove:
https://developer.spotify.com/documentation/web-api/reference/remove-library-items


## Windows setup script behavior
`setup-windows.ps1` installs missing Node.js LTS, Git, rustup/Rust MSVC and WebView2 where supported. The prerequisite checker does not fail just because an installable developer tool is missing; it reports it and the setup script performs the installation.
