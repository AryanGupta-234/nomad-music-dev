# NOMAD Music Stable v2 — Final Fix

This checkpoint addresses the Windows testing issues found during real desktop validation.

## Provider fixes
- Spotify provider status now distinguishes configured vs connected.
- Spotify desktop search uses the authenticated PKCE user session when connected.
- Spotify player token endpoint refreshes expired tokens.
- YouTube OAuth connections are reported as connected and user identity is stored.
- Health/provider UI now merges configuration and connection state.

## Playback fixes
- Spotify Web Playback SDK ready/device handling fixed.
- Local playback remains independent of Spotify/YouTube.
- YouTube results can play through the official embedded player stage.
- YouTube resolver now returns the video ID for embedding instead of a watch URL.
- Next/previous no longer collapse the existing queue.

## Lyrics fixes
- The lyrics endpoint now returns parsed LRC lines directly.
- Lyrics are fetched on demand when a track starts.
- Active lyric tracking follows local and Spotify playback position.

## UI rebuild
- Reworked the desktop WebView to use the older NOMAD visual language: graphite/glass surfaces, strong artwork cards, rails, immersive hero, floating player, source cards, polished playlist surfaces and dedicated lyrics/queue drawers.
- Added a real Connections modal with Connect/Sync actions for Spotify and YouTube.

## Configuration
- Local OAuth callback is `http://127.0.0.1:8765/api/v1/integrations/<provider>/callback`.
- `PUBLIC_BASE_URL` in `.env.example` is now aligned with the local API port.
- Tauri base dev config does not require the packaged Python sidecar; release config handles the sidecar.
