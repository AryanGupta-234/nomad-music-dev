# NOMAD Music Architecture

```text
Clients (Web / Mobile / future desktop)
              | HTTPS + REST + SSE
              v
        FastAPI application
              |
    +---------+---------+
    |                   |
 Track Graph       Services/Core
    |                   |
    +---------+---------+
              |
       SQLite / Cache
              |
       Background Workers
              |
 +------------+-----------------------------+
 | Spotify | YouTube | Deezer | Apple | ... |
 +-------------------------------------------+
```

## Server responsibilities

- Canonical music graph
- Provider synchronization
- Metadata/lyrics enrichment
- User listening events
- Taste profiles
- Recommendation candidate generation
- Vibe interpretation
- AI orchestration
- Cache and job state

## Client responsibilities

- UI
- Player controls
- Spotify Web Playback SDK integration when applicable
- Local/provider playback endpoint handling
- Lyrics presentation and animation
- Queue interaction

## Evolution path

SQLite is the initial single-instance database. Repository/service boundaries are intentionally kept independent of the database so a future PostgreSQL migration does not require a product rewrite.
