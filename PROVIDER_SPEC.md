# Provider Specification

Every provider implements the same interface and returns normalized models.

Required operations where supported:

- search
- get_track
- get_artist
- get_album
- list_user_playlists
- list_playlist_items
- sync_user_library
- resolve_playback

Provider adapters must never leak provider-specific response shapes into the UI.

Implemented in this starter:

- Mock provider
- Spotify adapter skeleton
- YouTube adapter skeleton
- lyrics adapter skeleton

Other provider modules are placeholders for incremental implementation.
