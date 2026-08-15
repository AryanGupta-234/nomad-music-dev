from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.tracks.service import upsert_provider_track
from app.db.models import Artist, Track
from app.providers.registry import music_providers
from app.core.profiles.service import get_or_create_default
from app.services.integrations import _oauth_get


async def spotify_user_search(db: Session, profile_id: str, query: str, limit: int = 10):
    """Search Spotify through the connected user's OAuth session.

    This deliberately uses the authenticated Spotify search endpoint rather than
    the client-credentials provider. That keeps user search aligned with PKCE and
    allows a connected desktop account to search even when no client secret is
    configured.
    """
    from app.providers.spotify.provider import SpotifyProvider

    data = await _oauth_get(
        db,
        "spotify",
        profile_id,
        "https://api.spotify.com/v1/search",
        {"q": query.strip(), "type": "track", "limit": max(1, min(limit, 10))},
    )
    items = (data.get("tracks") or {}).get("items") or []
    return [SpotifyProvider._map(item) for item in items]


def local_search(db: Session, q: str, limit: int = 20):
    term = f"%{q.strip().lower()}%"
    stmt = (
        select(Track)
        .join(Artist, Track.artist_id == Artist.id, isouter=True)
        .where(or_(Track.normalized_title.like(term), Artist.normalized_name.like(term)))
        .order_by(Track.updated_at.desc())
        .limit(limit)
    )
    return list(db.scalars(stmt))


async def federated_search(db: Session, q: str, limit: int = 20):
    providers = music_providers()
    per = max(2, min(8, limit // max(1, len(providers)) + 2))
    results = []
    seen_ids: set[tuple[str, str]] = set()
    seen_names: set[tuple[str, str]] = set()

    # Connected Spotify accounts get authenticated search first. This keeps the
    # desktop app on the PKCE/user-session path instead of requiring a client secret.
    try:
        profile = get_or_create_default(db)
        rows = await spotify_user_search(db, profile.id, q, min(limit, 10))
        for row in rows:
            key = (row.title.strip().lower(), row.artist.strip().lower())
            source_key = (row.provider, row.provider_id)
            if source_key in seen_ids or key in seen_names:
                continue
            seen_ids.add(source_key)
            seen_names.add(key)
            track = upsert_provider_track(db, row)
            results.append((track, row.provider))
            if len(results) >= limit:
                return results[:limit]
    except Exception:
        # A disconnected/expired Spotify session must not make federated search fail.
        pass

    for provider in providers:
        if getattr(provider, "name", "") == "spotify" and results:
            continue
        try:
            rows = await provider.search(q, per)
        except Exception:
            continue
        for row in rows:
            key = (row.title.strip().lower(), row.artist.strip().lower())
            source_key = (row.provider, row.provider_id)
            if source_key in seen_ids or key in seen_names:
                continue
            seen_ids.add(source_key)
            seen_names.add(key)
            track = upsert_provider_track(db, row)
            results.append((track, row.provider))
            if len(results) >= limit:
                return results[:limit]
    return results[:limit]
