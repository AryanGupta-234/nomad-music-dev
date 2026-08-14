# Database Schema

Initial entities:

- users
- profiles
- tracks
- track_sources
- track_aliases
- artists
- artist_sources
- artist_relations
- albums
- album_sources
- playlists
- playlist_items
- likes
- dislikes
- plays
- skips
- search_events
- recommendation_events
- lyrics
- lyrics_versions
- audio_features
- track_embeddings
- user_taste_profiles
- user_vibe_profiles
- provider_cache
- provider_sync_state
- recommendation_candidates
- release_events
- jobs
- job_runs

The starter migration creates the operational core and leaves room for enrichment tables to be added without changing the public API.
