from __future__ import annotations
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import TrackSource, Track

@dataclass
class PlaybackResolution:
    available: bool
    provider: str | None = None
    kind: str | None = None
    source: str | None = None
    track_id: str | None = None
    candidates: list[dict] | None = None
    reason: str | None = None

class PlaybackResolver:
    PRIORITY = {"local": 100, "spotify": 90, "audius": 70, "jamendo": 65, "youtube": 50, "deezer": 30, "apple": 20}

    def __init__(self, db: Session): self.db = db

    def _preferred_provider(self, track_id: str) -> str | None:
        return None

    def resolve(self, track_id: str, preferred_provider: str | None = None) -> PlaybackResolution:
        track = self.db.get(Track, track_id)
        if not track:
            return PlaybackResolution(False, track_id=track_id, reason="track_not_found", candidates=[])
        sources = list(self.db.scalars(select(TrackSource).where(TrackSource.track_id == track_id, TrackSource.available.is_(True))))
        if not sources:
            return PlaybackResolution(False, track_id=track_id, reason="no_playback_source", candidates=[])
        preferred = preferred_provider or self._preferred_provider(track_id)
        if preferred:
            sources.sort(key=lambda s: (0 if s.provider == preferred else 1, -self.PRIORITY.get(s.provider, 0)))
        else:
            sources.sort(key=lambda s: self.PRIORITY.get(s.provider, 0), reverse=True)
        def source_value(s):
            if s.provider == "youtube":
                return s.provider_id
            return s.uri or s.provider_id
        candidates=[{"provider":s.provider,"provider_id":s.provider_id,"kind":s.playback_kind or "external","source":source_value(s)} for s in sources]
        c=sources[0]
        return PlaybackResolution(True, provider=c.provider, kind=c.playback_kind or "external", source=source_value(c), track_id=track_id, candidates=candidates)
