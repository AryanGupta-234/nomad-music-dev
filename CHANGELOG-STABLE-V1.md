# NOMAD Music 1.0.0-stable-test

## Stable testing milestone

This release consolidates the local-first NOMAD Music architecture for end-to-end tester validation.

### Included

- Tauri 2 desktop shell
- React/Vite WebView UI
- local FastAPI sidecar
- SQLite database + Alembic
- canonical Track Graph
- provider source mappings
- Spotify + YouTube integration boundaries
- local music indexing/playback
- persistent player state + queue
- Smart Queue
- Smart Radio
- Vibe Journey
- recommendation scoring foundation
- Vibe intent parser
- playlist intelligence / Doctor baseline
- lyrics cache + synced LRC renderer
- local audio feature analysis baseline
- Windows WebView2 bootstrapper installation
- Windows setup/build scripts

### Testing scope

This is a **stable testing build**. Provider accounts are intentionally user-supplied, and external-provider behavior is credential/provider dependent.

The local backend must remain usable with zero external credentials.
