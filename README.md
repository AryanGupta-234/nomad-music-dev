# NOMAD Music

**Stable V3 — stabilization baseline**

NOMAD Music is a local-first unified music intelligence desktop application. V3 keeps the mature NOMAD feature surface while upgrading the visual system, reliability, real backend state, provider integration, queue correctness, and Windows desktop runtime.

> **Status:** Stable V3 development baseline. The repository is under an active stabilization pass; do not treat this as a final production release until the release checklist is green.

## V3 UI direction

V3 is an **upgrade of the existing full-feature NOMAD interface**, not a replacement with a simplified mock shell.

The current UI preserves the existing feature-rich `App.tsx` application and its corresponding `styles.css` design system while continuing to improve:

- artwork-led home hero and music rails;
- global/federated search;
- Discover and recommendation surfaces;
- local Library and indexing;
- Playlists and playlist tools;
- liked tracks/history flows;
- Smart Radio and Vibe Journey;
- NOMAD AI / Vibe and Playlist Doctor;
- Spotify / YouTube connection state;
- persistent player, queue, shuffle and repeat;
- synchronized lyrics;
- expanded now-playing experience;
- loading, error, empty and connection states.

The V3 entrypoint mounts `apps/desktop/ui/src/App.tsx`, preserving mature application behavior. `styles.css` remains the production design system and `nomad-polish.css` is a small additive V3 layer for interaction polish and responsive hardening. `AppV3.tsx` remains a prototype/reference shell and is not the production entrypoint.

## What changed in V3

### UI / UX

- Graphite / near-black visual system with glass-like surfaces.
- Existing full-feature NOMAD navigation retained.
- Artwork-led home hero, recommendation rails, discovery tiles and music cards retained.
- Unified Search, Discover, Library, Playlists, and AI / Vibe views retained.
- Persistent bottom player with seek, volume, shuffle, repeat, next/previous, and queue controls.
- Queue drawer and synchronized lyrics drawer.
- Source Hub for Spotify and YouTube connection state.
- Library indexing controls and playlist creation/viewing.
- Rich now-playing and expanded-player state.
- Added an additive `nomad-polish.css` layer for focus states, hover/active affordances, richer card/row transitions, player/drawer depth, narrow-WebView layouts, and reduced-motion support.
- Responsive desktop WebView layout remains an active hardening target; no production feature was removed to achieve the visual upgrade.
- Loading, error, empty, and connection states are represented instead of relying on fake connected UI.

### Playback / queue

- Normal next/previous queue progression.
- `repeat=one`, `repeat=all`, and repeat-off behavior.
- Shuffle without destroying canonical queue ordering.
- Queue/player state resolves against the real default profile rather than a literal `default` profile identifier.
- Local audio playback and provider resolution are surfaced through one player experience.
- Lyrics can be opened from the player or track rows and synchronized against local playback time.

### Search / provider sessions

- Federated search first attempts authenticated Spotify user search when a Spotify account is connected.
- Authenticated Spotify search uses the stored PKCE/OAuth session rather than the client-credentials provider.
- Expired authenticated sessions can refresh through the existing OAuth helper before retrying the request.
- If Spotify is disconnected or unavailable, federated search falls back to the configured provider registry instead of failing the entire search request.
- Fixed the V3 startup regression where `app.services.search.service` imported a removed `spotify_user_search` symbol from `app.services.integrations`, preventing Uvicorn from importing `app.main`.

### Database / desktop startup

The desktop sidecar has a migration bootstrap in `server/app/db/bootstrap.py`.

- Fresh databases run the Alembic migration chain.
- Existing legacy `create_all()` databases containing the expected core tables are detected and stamped at the current migration head instead of replaying incompatible CREATE TABLE migrations.
- Versioned databases are upgraded to Alembic `head` before the FastAPI application starts.
- `server/desktop_entry.py` creates a per-user desktop data directory and runs database bootstrap before starting Uvicorn.
- Production startup no longer depends on users manually running migration commands.

## Architecture

```text
NOMAD Music.exe
  ├── Tauri 2 desktop shell
  ├── React/Vite WebView
  │    ├── App.tsx                 <- production feature shell
  │    ├── styles.css              <- production UI system
  │    ├── nomad-polish.css        <- additive V3 UX/responsive polish
  │    └── backend-driven state
  └── bundled FastAPI/Python sidecar
       ├── Alembic + SQLite
       ├── background workers
       ├── provider adapters
       ├── Track Graph
       ├── queue/player state
       ├── recommendations / Smart Radio
       ├── lyrics
       └── AI / Vibe orchestration
```

The WebView is a client of the local API. Backend state remains the source of truth for queue/player/provider state; the UI should not invent connected or playing states.

## Current stabilization checklist

### BOOT

- [x] Tauri/WebView architecture
- [x] FastAPI sidecar entrypoint
- [x] Versioned database bootstrap
- [x] Legacy database detection
- [x] Local backend startup import regression fixed
- [ ] Full clean-machine release smoke test
- [ ] Final packaged sidecar verification

### CONNECTIONS

- [x] Spotify PKCE infrastructure
- [x] YouTube OAuth infrastructure
- [x] Provider connection status surface
- [ ] OAuth-state expiry and cleanup audit
- [ ] Token refresh end-to-end verification
- [ ] Reconnect / disconnect regression tests

### SEARCH

- [x] Local library search surface
- [x] Provider-backed search architecture
- [x] Unified result model
- [x] Authenticated Spotify user search path restored
- [x] Spotify-search startup import regression fixed
- [ ] Complete cross-provider dedupe/matching verification
- [ ] Provider fallback regression suite

### PLAYBACK

- [x] Local audio path
- [x] Queue persistence
- [x] Next / previous
- [x] Repeat one / all / off
- [x] Shuffle
- [x] Volume / seek
- [x] Player state tied to backend
- [ ] Spotify Web Playback end-to-end verification
- [ ] YouTube playback end-to-end verification
- [ ] Restart/persistence smoke test

### LYRICS

- [x] On-demand lyrics surface
- [x] Cached lyrics architecture
- [x] LRC/synchronized-line model
- [x] Playback synchronization UI
- [x] Seek-to-line interaction
- [ ] Provider coverage and offset regression suite

### LIBRARY

- [x] Local indexing surface
- [x] Canonical track model
- [x] Playlist creation/viewing
- [ ] Playlist add/remove/reorder verification
- [ ] Spotify library sync verification
- [ ] YouTube library sync verification
- [ ] Likes/history regression suite

### INTELLIGENCE

- [x] Recommendation architecture
- [x] Smart Radio surface
- [x] Vibe Journey surface
- [x] AI / Vibe surface
- [ ] Behavior-signal verification
- [ ] Playlist Doctor end-to-end verification
- [ ] AI fallback/error-path verification

### UI

- [x] Full-feature production shell restored as V3 baseline
- [x] Existing feature surface retained during V3 visual upgrade
- [x] Artwork-led home/discovery/player system
- [x] Additive interaction/hover/focus polish layer
- [x] Player/queue/lyrics drawers
- [x] Provider connection surface
- [x] Loading/error/empty feedback
- [ ] Full interaction audit for every button/action
- [ ] Desktop responsive regression pass
- [ ] Accessibility keyboard/focus pass
- [ ] Final visual polish pass

### DESKTOP / RELEASE

- [x] Windows desktop architecture
- [x] WebView2 installer configuration
- [x] User-local desktop data directory
- [x] Sidecar migration bootstrap
- [ ] Clean Windows install test
- [ ] Upgrade-from-V2 database test
- [ ] Bundled sidecar release test
- [ ] Final NSIS installer smoke test

## Development

Run the backend from `server/` on `127.0.0.1:8765`, then run the Tauri desktop app from `apps/desktop`.

The Vite entrypoint mounts the production feature shell `App.tsx` and loads `styles.css` plus the additive `nomad-polish.css` layer.

## Windows quick start

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-prereqs.ps1
.\scripts\windows\setup-windows.ps1
.\scripts\windows\run-local-backend.ps1
```

Run the full desktop development environment with:

```powershell
.\scripts\windows\dev.ps1
```

Build the installer:

```powershell
.\scripts\windows\build-release.ps1
```

NOMAD's NSIS installer is configured to install Microsoft Edge WebView2 automatically when it is missing. Users should not need to manually install WebView2 before installing NOMAD Music.

## Production build

1. Build the Python sidecar with `scripts/desktop/build-server.ps1` on Windows.
2. Install the Tauri CLI and Rust toolchain.
3. Run the desktop build from `apps/desktop`.
4. Smoke-test the packaged installer on a clean Windows environment.

Provider credentials remain server-side. Spotify/YouTube OAuth is handled through the local backend rather than exposing client secrets to the WebView.

## Documentation

- `API_SETUP.md` — API/provider setup.
- `docs/setup/INSTALLATION.md` — developer and release installation flow.
- `docs/setup/WEBVIEW2.md` — WebView2 installation behavior.
- `STABLE_TESTING_V2.md` — legacy V2 testing reference.
- `NOMAD-Music-Stable-v2-ONE-FILE-SETUP.md` — legacy V2 setup reference.

As V3 stabilization progresses, this README is updated with the current architecture, completed work, known gaps, and release checklist. The README is intended to remain the high-level source of truth for the state of the repository.

## Versioning policy

Until the final V3 release is cut, use **Stable V3 / stabilization baseline** for the development state. Individual commits should describe the subsystem changed (`fix(queue)`, `feat(ui)`, `fix(db)`, `docs`, etc.). Final release status should only be marked after the clean-install, migration-upgrade, provider, playback, and packaged-sidecar smoke tests are complete.
