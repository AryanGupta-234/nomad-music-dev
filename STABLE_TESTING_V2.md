# NOMAD Music — Stable Testing v2

## 1. Windows prerequisites

Run the prerequisite checker and installer from PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-prereqs.ps1
.\scripts\windows\setup-windows.ps1
```

The end-user installer uses Tauri/WebView2 bootstrap installation, so a user should not need to preinstall WebView2.

## 2. Configure local backend

Copy `.env.example` to `.env`. Set at minimum:

```env
PUBLIC_BASE_URL=http://127.0.0.1:8765
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_API_KEY=
```

Optional:

```env
GROQ_API_KEY=
GROQ_MODEL=
LASTFM_API_KEY=
GENIUS_API_KEY=
ACOUSTID_API_KEY=
```

## 3. Spotify

Register exactly:

```text
http://127.0.0.1:8765/api/v1/integrations/spotify/callback
```

Select Web Playback SDK for the desktop app. Stable v2 uses PKCE. Spotify Development Mode requires the app owner to have Premium and limits new apps to one Client ID per developer and five users.

## 4. YouTube

Enable YouTube Data API v3 and create a desktop/web OAuth client. Register:

```text
http://127.0.0.1:8765/api/v1/integrations/youtube/callback
```

## 5. Start local backend

```powershell
.\scripts\windows\run-local-backend.ps1
```

Check:

```text
http://127.0.0.1:8765/api/v1/health
http://127.0.0.1:8765/api/v1/health/providers
```

## 6. Run desktop application

```powershell
.\scripts\windows\dev.ps1
```

## 7. First test order

1. Launch NOMAD Music.
2. Index one local music folder.
3. Play a local track.
4. Open lyrics.
5. Test queue/repeat/shuffle.
6. Connect Spotify.
7. Sync Spotify library.
8. Search Spotify/local content together.
9. Connect YouTube.
10. Sync YouTube playlists.
11. Test canonical matching.
12. Test Smart Queue.
13. Test Smart Radio.
14. Test Vibe Journey.
15. Configure Groq and test AI controls.
16. Restart NOMAD and confirm SQLite state persists.

## 8. Spotify Stable v2 API behavior

NOMAD does not use removed February 2026 Spotify routes such as playlist `/tracks` management or entity-specific save/remove routes. Playlist contents use `/items`; library mutations use `/me/library`; search requests are limited to 10 items per call and must paginate for more.

## Spotify dashboard setup

For the current desktop app, select **Web Playback SDK**. Android, iOS and Ads API are not required for Stable v2 desktop testing. If the Spotify dashboard shows the Web API option disabled, do not block setup on that checkbox; NOMAD uses the current OAuth/Web API endpoints available to the Development Mode app.

Register exactly:

```text
http://127.0.0.1:8765/api/v1/integrations/spotify/callback
```

Do not replace `127.0.0.1` with `localhost`.
