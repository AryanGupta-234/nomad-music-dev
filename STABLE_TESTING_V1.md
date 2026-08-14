# NOMAD Music — Stable Testing v1

Version: 1.0.0-stable-test
Backend: local FastAPI + SQLite
Desktop: Tauri 2 + React/Vite + WebView2

## What this build is

This is the first consolidated testing release of the new NOMAD Music architecture. It is intentionally **local-first**:

- The user runs one Windows app (`NOMAD Music.exe`).
- Tauri owns the desktop window/WebView.
- A bundled FastAPI/Python sidecar provides the local backend.
- SQLite is the local source of truth.
- Background jobs run locally.
- Provider APIs are optional external integrations; the app still starts without them.

## Feature coverage

### Core / data model
- ✅ Canonical Track Graph
- ✅ Provider source mappings
- ✅ Reference-based playlists (playlist items point to tracks; playlists do not require downloaded audio)
- ✅ SQLite + Alembic
- ✅ Persistent player queue/state
- ✅ Behavioral signals and recommendation candidates
- ✅ Local filesystem library indexing

### Providers / integrations
- ✅ Provider abstraction
- ✅ Mock provider for offline testing
- ✅ Spotify catalog adapter
- ✅ YouTube catalog adapter
- ✅ Spotify OAuth scaffolding + connection storage
- ✅ YouTube OAuth scaffolding + connection storage
- ✅ Spotify/YouTube library reconciliation paths
- ✅ Deezer / Apple / Audius / Jamendo / SoundCloud module boundaries
- ✅ MusicBrainz / LRCLIB enrichment boundaries
- ⚠️ Real provider OAuth and playback require the tester's own credentials/connections

### Playback
- ✅ Unified PlaybackResolver
- ✅ Provider candidate reporting
- ✅ Local-file playback
- ✅ Persistent queue
- ✅ Next / previous
- ✅ Shuffle / repeat
- ✅ Persistent position / volume / player state
- ✅ Smart queue extension
- ✅ Spotify Web Playback command bridge (credential-gated)
- ⚠️ Provider-specific playback availability depends on the provider and connected account

### Lyrics
- ✅ LRCLIB integration
- ✅ Cached lyrics
- ✅ Background prefetch hooks
- ✅ LRC parsing
- ✅ Binary-search active lyric selection
- ✅ Persisted offset adjustment
- ✅ Desktop synced-lyrics UI foundation
- ⚠️ Coverage depends on external lyrics availability

### Intelligence
- ✅ Behavioral learning signals
- ✅ Taste/recommendation scoring foundation
- ✅ Persistent recommendation candidates
- ✅ Vibe intent parser
- ✅ Energy-aware sequencing
- ✅ Smart Queue
- ✅ Smart Radio
- ✅ Vibe Journey
- ✅ Playlist Doctor baseline
- ✅ Local audio feature analysis baseline
- ⚠️ Advanced semantic embeddings / ML ranking are optional extension points, not required for this test release
- ⚠️ LLM actions require an LLM provider key; deterministic recommendation flows work without one

### Product UI
- ✅ Home
- ✅ Search
- ✅ Discover
- ✅ Library
- ✅ Playlists
- ✅ Playlist intelligence/Doctor surface
- ✅ AI / Vibe surface
- ✅ Now Playing
- ✅ Queue
- ✅ Lyrics
- ✅ Local library indexing controls
- ✅ Tauri/WebView desktop shell
- ✅ WebView2 bootstrapper installer mode

### Desktop packaging
- ✅ Tauri 2 project
- ✅ FastAPI sidecar packaging path
- ✅ NSIS installer path
- ✅ WebView2 automatic bootstrapper path
- ✅ Windows prerequisite/setup scripts
- ⚠️ Final `.exe` installer must be compiled on Windows with the required Rust/MSVC toolchain
- ⚠️ Native global media keys / tray / notifications remain follow-up desktop polish

## Required for the first meaningful test

Only these are required to start the app locally:

1. Windows 10/11 64-bit
2. The bundled/installed WebView2 Runtime (the installer can bootstrap it automatically)
3. A successful local build or the provided installer

The following are optional and can be connected later:

- Spotify
- YouTube
- Groq
- Last.fm
- Genius
- AcoustID

## API connection map

| Provider | Purpose | Required? | Where to configure |
|---|---|---:|---|
| Spotify | catalog, user library, playlists, recent listening, Web Playback | Optional but recommended | `.env` / local Settings flow |
| YouTube | catalog/search, authenticated playlists/library reconciliation | Optional but recommended | `.env` |
| LRCLIB | lyrics + synced lyrics | Keyless | server provider |
| MusicBrainz | canonical metadata enrichment | Keyless | server provider |
| Deezer | catalog/search + preview metadata | Keyless for basic public search | server provider |
| Apple/iTunes | chart/release metadata + preview metadata | Keyless for current implementation | server provider |
| Audius | independent-catalog playback/search | Keyless | server provider |
| Jamendo | independent/CC catalog | Optional | server provider |
| SoundCloud | discovery/provider boundary | Optional | server provider |
| Last.fm | similar artists / enrichment | Optional | `LASTFM_API_KEY` |
| Genius | annotations/meaning features | Optional | `GENIUS_API_KEY` |
| AcoustID | acoustic fingerprint identification | Optional | `ACOUSTID_API_KEY` |
| Groq | natural-language AI / AI actions | Optional | `GROQ_API_KEY`, `GROQ_MODEL` |

## Environment file

Copy:

```powershell
Copy-Item .env.example .env
```

Then configure:

```env
APP_ENV=development
APP_SECRET_KEY=<random-long-secret>
PUBLIC_BASE_URL=http://127.0.0.1:8765
DATABASE_URL=sqlite:///./data/nomad.db

SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=

YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_API_KEY=

GROQ_API_KEY=
GROQ_MODEL=

LASTFM_API_KEY=
GENIUS_API_KEY=
ACOUSTID_API_KEY=
```

Do not put secrets into the frontend/WebView code.

## First test flow

1. Install the Windows build.
2. Launch `NOMAD Music`.
3. Confirm Home loads.
4. Open Settings / Integrations.
5. Connect Spotify if credentials are available.
6. Connect YouTube if credentials are available.
7. Add a local Music folder.
8. Index the folder.
9. Search for a track.
10. Open the track and inspect provider sources.
11. Play a local track.
12. Open Lyrics.
13. Create a playlist and add tracks.
14. Open Playlist Doctor.
15. Start Smart Radio.
16. Start a Vibe Journey.
17. Like/dislike tracks and verify recommendation behavior.
18. Restart NOMAD and verify the library/queue persist.

## Important testing expectation

A provider not being connected must **not** prevent the application from starting or local music from working.

Provider failures should degrade to:

- cached metadata,
- another available provider,
- local source,
- preview/fallback, or
- an honest unavailable state.

## Known limitations in v1

This is a stable **testing** build, not a claim that every advanced provider feature is production-certified. Specifically:

- Real Spotify/YouTube account testing requires the tester's own OAuth configuration.
- Spotify playback remains dependent on the connected account/provider rules.
- Advanced semantic embeddings and sophisticated collaborative learning are still extension points.
- Native Windows global media-key/tray/notification polish is not the acceptance criterion for this build.
- The final signed Windows installer must be built on Windows.
