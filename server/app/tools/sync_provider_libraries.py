"""One-shot V4.1 provider library synchronizer.

Run from server/ after OAuth accounts have been connected:
    python -m app.tools.sync_provider_libraries

The command synchronizes Spotify and YouTube into the canonical NOMAD graph,
then materializes a unified `NOMAD · History` playlist from NOMAD play events.
Spotify recently-played entries are imported by the provider sync; YouTube's
private watch history is intentionally not fabricated because the YouTube Data
API does not expose it.
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.profiles.service import get_or_create_default
from app.db.models import PlayEvent, Playlist, PlaylistItem, Track
from app.db.session import SessionLocal
from app.services.integrations import sync_all_libraries


def materialize_history(db, profile_id: str, limit: int = 200) -> dict:
    """Create/update a normal NOMAD playlist from recent play events.

    History remains an event stream in the database; this playlist is only a
    convenient stable presentation of the latest unique played tracks.
    """
    playlist = db.scalar(select(Playlist).where(Playlist.name == "NOMAD · History"))
    if not playlist:
        playlist = Playlist(
            name="NOMAD · History",
            description="Unified playback history from NOMAD and connected providers.",
        )
        db.add(playlist)
        db.flush()

    events = list(
        db.scalars(
            select(PlayEvent)
            .where(PlayEvent.profile_id == profile_id)
            .order_by(PlayEvent.created_at.desc())
            .limit(limit * 3)
        )
    )
    seen: set[str] = set()
    track_ids: list[str] = []
    for event in events:
        if not event.track_id or event.track_id in seen:
            continue
        if not db.get(Track, event.track_id):
            continue
        seen.add(event.track_id)
        track_ids.append(event.track_id)
        if len(track_ids) >= limit:
            break

    existing = list(
        db.scalars(
            select(PlaylistItem)
            .where(PlaylistItem.playlist_id == playlist.id)
            .order_by(PlaylistItem.position)
        )
    )
    by_track = {item.track_id: item for item in existing}
    wanted = set(track_ids)
    for item in existing:
        if item.track_id not in wanted:
            db.delete(item)
    db.flush()

    for position, track_id in enumerate(track_ids):
        item = by_track.get(track_id)
        if item:
            item.position = position
        else:
            db.add(PlaylistItem(playlist_id=playlist.id, track_id=track_id, position=position))

    db.commit()
    return {"playlist_id": playlist.id, "tracks": len(track_ids)}


async def main() -> None:
    db = SessionLocal()
    try:
        profile = get_or_create_default(db)
        result = await sync_all_libraries(db, profile.id)
        result["history"] = materialize_history(db, profile.id)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
