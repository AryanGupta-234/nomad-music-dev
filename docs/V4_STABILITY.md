# NOMAD V4 Stability Contract

## Objective

V4 is a stabilization pass over the existing NOMAD application. It must preserve the mature UI/features while making provider data, playback state, history, playlists, artwork, and authentication behave consistently.

## Canonical data contract

A provider track is never a separate UI-only object. It is normalized into the NOMAD graph:

```text
Track
├── Artist
├── Album
├── TrackSource(local)
├── TrackSource(spotify)
└── TrackSource(youtube)
```

The UI should consume the canonical track and its sources instead of maintaining separate Spotify and YouTube copies of the same song.

## Default library behavior

When a provider account is connected and synchronized:

- Spotify saved tracks enter the normal NOMAD library.
- Spotify playlists become NOMAD playlists with provider metadata.
- Spotify recently played is represented as NOMAD playback history.
- YouTube liked videos enter the normal NOMAD library when exposed by the Data API.
- YouTube playlists become NOMAD playlists.
- YouTube playback performed through NOMAD creates NOMAD history events.
- Local files remain first-class tracks and can coexist with provider sources.

The backend should therefore expose a combined library rather than forcing the frontend to select one provider before seeing data.

## History limitation

Spotify exposes recently played through its Web API and V4 imports that data during provider sync.

The YouTube Data API does not expose a user's private watch-history feed. V4 must not fabricate YouTube history. Instead, NOMAD records YouTube plays that actually occur through NOMAD and imports YouTube likes/playlists as library data.

## Sync guarantees

Provider synchronization is best-effort and isolated:

```text
sync-all
  ├── Spotify ──┐
  │             ├── success/failure independently
  └── YouTube ──┘
```

A Spotify token/API failure must not erase or prevent existing YouTube/local data, and vice versa.

Access tokens are refreshed before authenticated provider requests when an expiry timestamp is available.

## Artwork contract

1. Prefer the highest resolution provider artwork.
2. Preserve provider-specific source metadata.
3. Never apply CSS blur/filter to artwork surfaces.
4. Allow an explicit provider resync to upgrade old database rows.
5. Do not claim that a low-resolution provider source can be made losslessly sharper.

## Playback contract

The resolver must never select a provider source whose account is disconnected.

```text
local       -> local HTML5 audio
spotify     -> Spotify Web Playback / eligible authenticated playback
youtube     -> embedded YouTube player integration
```

Metadata presence alone is not playback availability.

## Release gates

V4 is not final until these pass on Windows:

- fresh install;
- existing V3 database upgrade;
- backend boot with no import errors;
- Spotify OAuth + refresh + library sync;
- YouTube OAuth + library sync;
- combined library shows local + Spotify + YouTube sources;
- Spotify recent-played history import;
- YouTube NOMAD playback creates history;
- local playback;
- Spotify playback;
- embedded YouTube playback;
- queue next/previous/shuffle/repeat;
- lyrics sync;
- artwork migration/resync;
- packaged Tauri/WebView2 installer;
- no blank WebView on production build.

## Manual verification after pulling V4

```powershell
cd E:\nomad\nomad-git
git pull origin main

# Make sure no stale backend owns 8765.
Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue |
  Select-Object LocalAddress,LocalPort,OwningProcess

# Start the backend.
.\scripts\windows\run-local-backend.ps1
```

Then connect Spotify and YouTube through **Connections**. API keys/client credentials only make providers configured; OAuth authorization is required before private library data can be synchronized.

After both accounts are connected, use the application's provider sync action if present. If the current UI does not yet expose a combined sync action, the backend integration service contains the V4 best-effort sync orchestration and the UI should be wired to it before release.
