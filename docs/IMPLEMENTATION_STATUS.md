# NOMAD Music — implementation status

## Stable Testing v2 — 2.0.0-stable-test

### Core
- [x] FastAPI local API
- [x] SQLite + SQLAlchemy
- [x] Alembic migrations
- [x] Canonical Track Graph
- [x] Provider source mappings
- [x] Reference-based playlists
- [x] Persistent player queue/state
- [x] Behavioral signals / recommendation candidates
- [x] Local filesystem indexing

### Providers
- [x] Provider interfaces
- [x] Mock provider
- [x] Spotify catalog adapter
- [x] YouTube catalog adapter
- [x] Spotify OAuth connection scaffolding
- [x] YouTube OAuth connection scaffolding
- [x] Spotify library reconciliation path
- [x] YouTube library reconciliation path
- [x] Deezer / Apple / Audius / Jamendo / SoundCloud boundaries
- [x] MusicBrainz / LRCLIB boundaries
- [ ] Real credential integration verification (requires tester credentials)

### Playback
- [x] Unified PlaybackResolver
- [x] Provider candidate reporting
- [x] Local-file playback
- [x] Persistent queue
- [x] Next / previous
- [x] Shuffle / repeat
- [x] Persistent position / volume
- [x] Smart queue extension
- [x] Spotify Web Playback bridge
- [ ] Provider-specific full-track availability certification

### Intelligence
- [x] Behavioral learning signals
- [x] Recommendation ranking foundation
- [x] Persistent recommendation candidates
- [x] Vibe intent parser
- [x] Energy-aware sequencing
- [x] Smart Radio
- [x] Vibe Journey
- [x] Playlist Doctor baseline
- [x] Local audio feature baseline
- [ ] Advanced semantic embeddings / ML ranking
- [ ] Full multi-step LLM agent

### Lyrics
- [x] Lyrics persistence
- [x] LRCLIB
- [x] Background prefetch hooks
- [x] LRC parser
- [x] Active-line calculation
- [x] Offset persistence
- [x] Desktop synced lyrics UI

### Desktop
- [x] Tauri 2 shell
- [x] React/Vite WebView UI
- [x] FastAPI sidecar packaging path
- [x] Windows WebView2 bootstrapper path
- [x] Music-first Home/Search/Discover/Library/Playlists/AI surfaces
- [x] Player / Queue / Lyrics surfaces
- [ ] Native global media keys
- [ ] Tray lifecycle polish
- [ ] Native notifications
- [ ] Signed/released production installer

### Mobile
- [ ] React Native client
- [ ] Shared API client package
- [ ] Mobile playback integration

## Stability statement

Stable Testing v2 means the **local-first desktop architecture and agreed baseline music experience are integrated and ready for tester validation**. It does not claim external providers or advanced ML/LLM features are independently production-certified without credentials/model configuration.
