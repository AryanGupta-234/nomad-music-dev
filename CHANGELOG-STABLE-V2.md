# NOMAD Music — Stable Testing v2

## Spotify 2026 Development Mode hardening

Stable v2 updates the Spotify integration for the February/March 2026 Development Mode API changes.

### Included
- Spotify PKCE authorization for the desktop/local OAuth flow.
- Spotify client secret is optional for PKCE desktop authorization; keep it configured only when required by your app/account setup.
- Spotify search is capped at the current Development Mode maximum of 10 results per request.
- Playlist item integration uses `/playlists/{id}/items`.
- Spotify library sync continues to use the still-available `/me/tracks` and `/me/playlists` read endpoints.
- Generic Spotify library save/remove support uses `PUT/DELETE /me/library`.
- Spotify playback scopes include playback-state and modify-playback-state scopes needed by the desktop player bridge.
- Missing Spotify response fields are treated as optional.

## Product/runtime
- Local-only FastAPI + SQLite backend.
- Tauri desktop/WebView2 client.
- No cloud database or cloud worker required.

## Verification

- 16 automated backend tests passing.
- Fresh Alembic database reaches revision `0008_spotify_pkce`.
- Spotify PKCE authorization URL generation is covered by tests.
- Spotify search request limit is covered by tests.

## Windows setup fix
- prerequisite checker no longer fails on scalar PowerShell objects
- Node.js/Git/rustup can be installed automatically via winget during setup
- Rust MSVC toolchain is installed from rustup before build
- WebView2 detection handles scalar version results safely
