from __future__ import annotations
import asyncio
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Track, Lyrics, Artist
from app.providers.lyrics.lrclib import LRCLIBProvider

async def enrich_track(db: Session, track_id: str, refresh: bool = False):
    track = db.get(Track, track_id)
    if not track:
        return {"ok": False, "reason": "track_not_found"}
    cached = db.scalar(select(Lyrics).where(Lyrics.track_id == track_id))
    if cached and (cached.plain_lyrics or cached.synced_lyrics) and not refresh:
        return {"ok": True, "cached": True, "found": True}
    artist = db.get(Artist, track.artist_id) if track.artist_id else None
    result = await LRCLIBProvider().search(track.title, artist.name if artist else "", track.duration_ms)
    if not result:
        return {"ok": True, "cached": False, "found": False}
    if not cached:
        cached = Lyrics(track_id=track_id); db.add(cached)
    cached.plain_lyrics = result.get("plain", "")
    cached.synced_lyrics = result.get("synced", "")
    cached.source = result.get("source")
    db.commit()
    return {"ok": True, "cached": False, "found": True}

async def enrich_batch(db: Session, limit: int = 10):
    tracks = db.scalars(select(Track).order_by(Track.updated_at.desc()).limit(max(1, min(limit, 50)))).all()
    out=[]
    for track in tracks:
        out.append(await enrich_track(db, track.id))
        await asyncio.sleep(0)
    return out
