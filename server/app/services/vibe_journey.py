from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Track
from app.intelligence.sequencing.engine import vibe_journey


def build_vibe_journey(db: Session, target_minutes: int = 45, limit: int = 30) -> list[dict]:
    tracks = list(db.scalars(select(Track).order_by(Track.updated_at.desc()).limit(limit * 4)))
    rows = [
        {
            "id": t.id,
            "title": t.title,
            "duration_ms": t.duration_ms or 0,
            "artist": t.artist_id or "",
            "artwork_url": t.artwork_url,
            "energy": 0.5,
        }
        for t in tracks
    ]
    return vibe_journey(rows, target_minutes=target_minutes)[:limit]
