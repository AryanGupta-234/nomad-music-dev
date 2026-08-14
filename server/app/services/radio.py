from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Track, TrackSource, UserSignal
from app.services.recommendations.service import recommend
from app.intelligence.sequencing.engine import sequence_tracks


def smart_radio(db: Session, profile_id: str | None, seed_track_id: str | None, limit: int = 20) -> list[dict]:
    candidates: dict[str, dict] = {}
    if seed_track_id:
        seed = db.get(Track, seed_track_id)
        if seed:
            candidates[seed.id] = {
                "id": seed.id,
                "title": seed.title,
                "duration_ms": seed.duration_ms or 0,
                "artist": seed.artist_id or "",
                "artwork_url": seed.artwork_url,
                "energy": 0.55,
                "seed": True,
            }
    for candidate, score in recommend(db, profile_id, limit=max(limit * 3, 50)):
        t = db.get(Track, candidate.track_id)
        if not t:
            continue
        candidates.setdefault(t.id, {
            "id": t.id,
            "title": t.title,
            "duration_ms": t.duration_ms or 0,
            "artist": t.artist_id or "",
            "artwork_url": t.artwork_url,
            "energy": 0.5 + (candidate.similarity - 0.5) * 0.6,
            "score": round(float(score), 4),
        })
    rows = list(candidates.values())[: max(limit * 4, limit)]
    return sequence_tracks(rows, target_minutes=None, avoid_repeats=True)[:limit]
