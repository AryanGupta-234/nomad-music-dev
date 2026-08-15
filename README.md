# NOMAD Music

**Stable V4.1 — unified provider/data stabilization baseline**

NOMAD Music is a local-first unified music intelligence desktop application. V4.1 keeps the mature V3 feature surface and makes the canonical Track Graph explicitly provider-aware: local, Spotify, and YouTube metadata can coexist on the same NOMAD track while imported provider playlists and Spotify recent-played events feed the local backend.

> **Status:** Stable V4.1 development baseline. Provider playback and packaged-release smoke tests are still required before calling this a final production release.

## V4 goals

```text
                 NOMAD CANONICAL TRACK GRAPH
                         │
          ┌──────────────┼──────────────┐
          │              │              │
        LOCAL         SPOTIFY        YOUTUBE
          │              │              │
       audio         liked/tracks    likes/playlists
       files         playlists       metadata
                       recent play
          └──────────────┼──────────────┘
                         │
             Library / History / Playlists
                         │
                 Player / Queue / AI
```

The important rule is **do not create three isolated libraries**. Provider results are normalized into the same Track/TrackSource graph. A track may therefore expose multiple sources and can be used by the same library, playlist, queue, lyrics, artwork, recommendation, and intelligence systems.

## V4.1 provider data behavior

### Spotify

When the user's Spotify account is actually connected through OAuth, V4.1 imports:

- saved/liked tracks;
- Spotify playlists and playlist membership;
- provider artwork and metadata;
- Spotify recently-played tracks into NOMAD play-event history;
- provider source IDs so playback can resolve Spotify separately from local/YouTube sources.

OAuth credentials in `.env` are configuration only. They do not themselves connect a Spotify account.

### YouTube

When the user's Google/YouTube account is connected through OAuth, V4.1 imports:

- YouTube liked videos when the API exposes the account's likes playlist;
- owned YouTube playlists and playlist membership;
- video title/channel/artwork metadata;
- YouTube source IDs and URLs in the canonical TrackSource graph.

**Important API limitation:** the YouTube Data API does not expose a user's private watch-history feed to NOMAD. V4.1 therefore does **not** fabricate YouTube history. YouTube likes/playlists are imported; NOMAD playback events become history when the user plays a YouTube track through NOMAD.

### Local

Local indexed audio remains a first-class source and is never overwritten by remote provider metadata merely because a remote copy exists. The canonical track can contain local + Spotify + YouTube sources together.

## Unified sync

The integration service exposes `sync_all_libraries(db, profile_id)`. Spotify and YouTube are attempted independently: one provider failing authentication/API access must not discard the other provider's successfully imported data.

For a connected Spotify account, sync also refreshes expiring access tokens before authenticated calls and imports recently-played metadata.

For YouTube, sync uses the authenticated Data API for likes/playlists and deliberately reports that private history is unsupported rather than creating false history records.

### Unified history playlist

V4.1 also materializes a normal NOMAD playlist named **`NOMAD · History`** after provider synchronization. It is generated from NOMAD `PlayEvent` records and contains the latest unique played tracks for the default profile.

That means Spotify recently-played tracks imported during sync and tracks played locally/in NOMAD can appear together in one history playlist. YouTube history is included when NOMAD itself records a YouTube play; private YouTube watch history is not guessed.

Run the complete sync + history materialization from `server/`:

```powershell
python -m app.tools.sync_provider_libraries
```

The command prints independent Spotify/YouTube results plus the history playlist result. A provider failure is reported rather than silently deleting or replacing another provider's data.

## V3 features retained

- Graphite / near-black visual system with glass surfaces.
- Artwork-led home hero and music rails.
- Global/federated search.
- Discover and recommendation surfaces.
- Local Library and indexing.
- Playlists and Playlist Doctor.
- Likes/history flows.
- Smart Radio and Vibe Journey.
- NOMAD AI / Vibe.
- Spotify / YouTube connection state.
- Persistent player, queue, shuffle and repeat.
- Synchronized lyrics.
- Expanded now-playing experience.
- Loading, error, empty, and connection states.
- Local vector navigation icons and responsive polish layer.

## Connection model

`configured != connected`.

```text
.env credentials
      │
      ▼
provider configured
      │
      │ OAuth / user authorization
      ▼
IntegrationAccount
      │
      ├── access token
      ├── refresh token
      └── provider user ID
      │
      ▼
authenticated provider data
```

Spotify callback:

```text
http://127.0.0.1:8765/api/v1/integrations/spotify/callback
```

YouTube callback:

```text
http://127.0.0.1:8765/api/v1/integrations/youtube/callback
```

These exact callback URLs must also be configured in the provider consoles when using the local development backend.

## Artwork V4

- Spotify chooses the largest returned album image based on dimensions.
- YouTube prefers `maxresdefault.jpg` for known video IDs and falls back to API thumbnails.
- Imported YouTube playlist items use the highest available thumbnail before falling back.
- Existing database rows require a provider re-sync to receive improved artwork URLs.
- UI artwork surfaces explicitly suppress accidental CSS blur/filter effects.

## Playback V4

Playback source selection is provider-aware. A disconnected Spotify/YouTube source is not selected merely because its metadata exists.

```text
Track
 ├── local source       → HTML5/local audio
 ├── spotify source     → Spotify Web Playback eligibility required
 └── youtube source     → YouTube player integration required
```

The resolver reports `provider_not_connected` when every available source requires a provider account that is not authenticated.

**Current release caveat:** YouTube metadata import is implemented, but a production-grade embedded YouTube player and Spotify Web Playback end-to-end test still need to be completed before V4.1 is considered a final release.

## History semantics

NOMAD history is **playback history inside NOMAD**, not a claim that every provider exposes private history.

- Local tracks played in NOMAD → `PlayEvent`.
- Spotify recently played → imported into `PlayEvent` during Spotify library sync.
- YouTube tracks played in NOMAD → `PlayEvent` when NOMAD records playback.
- YouTube private watch history → not imported because the Data API does not expose it.
- `NOMAD · History` → materialized from the latest unique NOMAD play events after the V4.1 sync command.

This keeps the backend honest and gives Library/Playlists a single history surface without inventing provider data.

## Stability checklist

### BOOT

- [x] FastAPI/Tauri architecture
- [x] Local backend startup
- [x] Provider startup import regression fixed
- [x] Production blank-screen helper regression fixed
- [ ] Clean-machine packaged release smoke test

### CONNECTIONS

- [x] Spotify PKCE OAuth
- [x] YouTube OAuth
- [x] Configured vs connected status
- [x] Token refresh helper for authenticated provider calls
- [x] Provider-isolated sync failure handling
- [ ] Provider-console redirect URI verification
- [ ] Full reconnect/disconnect regression suite

### DATA / SYNC

- [x] Canonical Track + TrackSource model
- [x] Spotify saved tracks import
- [x] Spotify playlist import
- [x] Spotify recently-played import
- [x] YouTube likes import where exposed
- [x] YouTube playlist import
- [x] Provider source metadata preserved
- [x] One provider failure does not discard the other provider's sync
- [x] Unified `NOMAD · History` playlist materialization
- [ ] Automatic scheduled/background sync wiring
- [ ] Full cross-provider identity/dedupe regression suite

### LIBRARY / PLAYLISTS

- [x] Local library
- [x] Provider imported tracks use the same canonical graph
- [x] Imported provider playlists become NOMAD playlists
- [x] Playlist membership reconciliation
- [x] Unified history playlist
- [ ] Full playlist editing regression suite
- [ ] Duplicate playlist-name UX refinement

### HISTORY / INTELLIGENCE

- [x] NOMAD playback events
- [x] Spotify recently-played ingestion
- [x] YouTube playback can feed NOMAD events
- [x] Honest YouTube history limitation
- [x] History playlist materialization
- [ ] History UI provider filters
- [ ] Deduplicated event ingestion using provider timestamps
- [ ] Recommendation regression suite against imported provider behavior

### PLAYBACK

- [x] Local audio resolution
- [x] Queue persistence
- [x] Next / previous
- [x] Shuffle
- [x] Repeat one / all / off
- [x] Disconnected provider guard
- [ ] Spotify Web Playback end-to-end verification
- [ ] Embedded YouTube playback
- [ ] Source failover end-to-end

### ARTWORK / UI

- [x] Highest-resolution Spotify artwork selection
- [x] High-resolution YouTube artwork selection
- [x] CSS blur/filter suppression
- [x] Vector navigation icons
- [x] Responsive polish layer
- [ ] Existing-library artwork migration pass
- [ ] Hero/player `<img srcset>` optimization
- [ ] Full button/interaction audit

## Windows quick start

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\windows\check-prereqs.ps1
.\scripts\windows\setup-windows.ps1
.\scripts\windows\run-local-backend.ps1
```

If port `8765` is already occupied:

```powershell
Get-NetTCPConnection -LocalPort 8765 -State Listen | Select-Object OwningProcess
Stop-Process -Id <PID> -Force
```

Run the desktop environment with:

```powershell
.\scripts\windows\dev.ps1
```

## Provider setup

The relevant server-side variables are:

```text
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_API_KEY=
PUBLIC_BASE_URL=http://127.0.0.1:8765
```

Do not commit real secrets to Git. The `.env` file is local configuration.

## Repository

urlNOMAD Music on GitHubhttps://github.com/AryanGupta-234/nomad-music-dev

V4.1 is the stabilization branch of the existing NOMAD product, not a UI-only rewrite. Changes should preserve working V3 behavior while improving reliability and provider integration incrementally.
