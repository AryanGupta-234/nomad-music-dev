# NOMAD Music — API / Provider Setup

This document is the single place to configure external services for Stable Testing v1.

## 1. Spotify — recommended (current 2026 setup)

Used for:

- catalog metadata/search
- authenticated playlists
- saved tracks
- user-library reconciliation
- recent listening where permitted
- Web Playback SDK bridge

Set:

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
```

For Stable v2, the desktop OAuth flow uses PKCE. `SPOTIFY_CLIENT_SECRET` may remain blank for the PKCE authorization exchange; keep it configured if your Spotify app/account setup uses it for server-side token refresh. The owner of a new Spotify Development Mode app needs Premium, and new apps are limited to one Client ID per developer and five users.

The local backend handles the OAuth callback and keeps provider credentials out of the WebView.

For the local desktop callback, register exactly:

```text
http://127.0.0.1:8765/api/v1/integrations/spotify/callback
```

Use `127.0.0.1` rather than `localhost`.

## 2. YouTube — recommended

Used for:

- catalog/search
- authenticated playlist/library reconciliation
- provider identity mapping

Set:

```env
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_API_KEY=
```

Create/enable the YouTube Data API in the Google Cloud project that owns the OAuth client.

## 3. LRCLIB — no key

Used for:

- plain lyrics
- synced LRC lyrics
- lyrics indexing/background prefetch

Nothing needs to be added to `.env`.

## 4. MusicBrainz — no key for the current adapter boundary

Used for canonical metadata enrichment and identity support.

Nothing needs to be added to `.env` for the initial test build.

## 5. Deezer — no key for current public-search adapter

Used for catalog/search/preview metadata.

Nothing needs to be added to `.env` for the initial test build.

## 6. Apple / iTunes — no key for current metadata/preview path

Used for chart/release metadata and preview information where supported by the current provider adapter.

Nothing needs to be added to `.env` for the initial test build.

## 7. Audius — no key for current adapter boundary

Used for independent-catalog discovery/playback candidates.

Nothing needs to be added to `.env` for the initial test build.

## 8. Jamendo — optional

Used for independent / open-license catalog coverage.

Configure only if the provider adapter you enable requires a client identifier.

## 9. SoundCloud — optional

Used as an additional discovery/provider boundary.

Configure only when the provider adapter is enabled.

## 10. Last.fm — optional

Used for artist similarity and enrichment.

```env
LASTFM_API_KEY=
```

## 11. Genius — optional

Used for song meaning/annotation-style features where the adapter is enabled.

```env
GENIUS_API_KEY=
```

## 12. AcoustID — optional

Used for acoustic fingerprint identification.

```env
ACOUSTID_API_KEY=
```

## 13. Groq — optional but recommended for AI natural language

Used for:

- intent interpretation
- AI playlist instructions
- explanations
- AI action layer

```env
GROQ_API_KEY=
GROQ_MODEL=
```

The deterministic Vibe/recommendation engine must still function when these are blank.

## Credential rules

Never put provider client secrets, refresh tokens, or API secrets into `apps/desktop/ui` or any TypeScript source.

Provider credentials belong to the local backend environment.

## Connectivity verification

After configuration, use:

```text
GET /api/v1/health/providers
GET /api/v1/integrations/connections
```

and then test:

```text
GET /api/v1/search?q=<song>
POST /api/v1/integrations/spotify/sync
POST /api/v1/integrations/youtube/sync
GET /api/v1/tracks/<id>/resolve
GET /api/v1/tracks/<id>/lyrics
```

A provider failing health checks should not prevent local NOMAD startup.

## Spotify 2026 Development Mode notes

Spotify reduced Development Mode in 2026. Current limits include Premium for the app owner, one Client ID per developer, and five users per app. The current Web API migration renamed playlist item routes from `/tracks` to `/items`, reduced search `limit` to a maximum of 10, removed several batch/browse endpoints, and added generic `/me/library` save/remove/contains endpoints. NOMAD Stable v2 is implemented against those rules.

The current app still reads saved tracks via `GET /me/tracks`, current-user playlists via `GET /me/playlists`, playlist contents via `GET /playlists/{id}/items`, and uses the Web Playback SDK for Spotify-controlled playback.

## Official Spotify references used by Stable v2

- Development Mode migration: https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
- February 2026 API changelog: https://developer.spotify.com/documentation/web-api/references/changes/february-2026
- Save items to library: https://developer.spotify.com/documentation/web-api/reference/save-library-items
- Remove items from library: https://developer.spotify.com/documentation/web-api/reference/remove-library-items
- Web Playback SDK: https://developer.spotify.com/documentation/web-playback-sdk/reference
