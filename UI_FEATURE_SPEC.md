# NOMAD UI Foundation

This document is the source-of-truth inventory for the new NOMAD desktop UI. The UI is music-first, provider-agnostic, local-first, and designed around one canonical Track object.

## Primary surfaces
- Home: Continue Listening, Made For You, Your Vibe, New For You, Recently Played, Trending.
- Search: songs, artists, albums, playlists and lyrics through one unified search box.
- Discover: For You, New Releases, Hidden Gems, Trending, Genres, Global, Smart Radio and Vibe Journey.
- Library: Liked Songs, Playlists, Albums, Artists, Local Music, Downloads and Recently Played.
- AI / Vibe: natural-language music intent, Vibe Match, Smart Radio, Playlist Doctor and AI controls.

## Global UI
- Persistent bottom player.
- Universal track cards and rows with play, like, add, queue, lyrics, artist, album, radio and more actions.
- SVG icon system; no emoji used as primary controls.
- Dark graphite/glass visual system with artwork-derived accent color.
- Responsive desktop/mobile behavior, loading skeletons, resolving states, toasts and graceful errors.
- Docked lyrics drawer plus fullscreen lyrics mode.
- Queue drawer, source hub, playlist creation and reusable modal primitives.

## Player
- Play/pause, previous, next, seek, volume, shuffle, repeat, queue, lyrics and like.
- Single playback owner.
- Source Resolver status: resolving, ready, playing, buffering and unavailable.
- Adjacent-track prefetch and queue-aware navigation.

## Intelligence UI
- Song DNA: BPM, key/Camelot, energy, danceability, acousticness, loudness, mood.
- Playlist DNA: aggregate tempo, energy, dance, acousticness, mood and key compatibility.
- Why This: data-backed recommendation explanations.
- Smart Queue: taste similarity, vibe similarity, BPM/key compatibility, energy continuity, diversity and recent-repeat penalties.
- Auto Radio: candidate generation, scoring, sequencing and discovery.
- Energy Journey: chill -> groove -> peak -> cooldown.
- Playlist Doctor: duplicates, metadata gaps, repeated artists, energy jumps and transition issues.

## UI algorithms
1. Artwork accent extraction and blurred background theming.
2. Lazy image loading and staggered card entry.
3. Horizontal rail wheel-to-scroll and edge-aware arrow navigation.
4. Provider fan-out, normalization, deduplication and relevance ranking.
5. Canonical Track identity and source availability display.
6. Source resolution and provider fallback.
7. Queue generation, shuffle, repeat and artist-spacing rules.
8. Audio-clock progress updates and binary-search lyric synchronization.
9. Like, replay, completion, skip, search and playlist signals as recommendation inputs.
10. Recommendation scoring with similarity, vibe, context, freshness, exploration and repetition penalties.
11. BPM/Camelot/energy transition scoring for radio and DJ-style sequencing.
12. Background refresh with instant cached/local rendering.

## Provider abstraction
Spotify, YouTube, Deezer, Apple, Audius, Jamendo, SoundCloud and local files are playback/metadata sources. Users interact with NOMAD Tracks, not provider-specific track objects.

## Design rule
The UI must never require the user to understand which provider owns a result. A track is a NOMAD Track; provider identity is secondary metadata and a resolver concern.
