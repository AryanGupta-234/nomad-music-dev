# API Contract v1

Base: `/api/v1`

## Health

- `GET /health`
- `GET /health/providers`

## Tracks

- `GET /tracks/{track_id}`
- `GET /tracks/{track_id}/lyrics`
- `GET /tracks/{track_id}/related`
- `GET /tracks/{track_id}/resolve`

## Search

- `GET /search?q=`
- `GET /search/suggestions?q=`

## Library

- `GET /library`
- `GET /library/liked`

## Playlists

- `GET /playlists`
- `POST /playlists`
- `GET /playlists/{id}`
- `PATCH /playlists/{id}`
- `DELETE /playlists/{id}`
- `POST /playlists/{id}/items`
- `DELETE /playlists/{id}/items/{item_id}`

## Recommendations

- `GET /recommendations`
- `GET /vibe?q=`

## Events

- `POST /events/play`
- `POST /events/skip`
- `POST /events/like`
- `POST /events/search`

## Integrations

- `GET /integrations`
- `GET /integrations/spotify/connect`
- `GET /integrations/youtube/connect`
- `POST /integrations/{provider}/sync`

## Realtime

- `GET /events/stream` — server-sent event channel for sync/job/cache updates.

All contracts should remain provider-agnostic so the same API is consumed by web and future mobile clients.
