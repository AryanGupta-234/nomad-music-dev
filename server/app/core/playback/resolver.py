from __future__ import annotations

from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import IntegrationAccount, TrackSource, Track

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
    # YouTube is an official embedded playback source and does not require
    # OAuth merely to play a public video. OAuth is used for the user's library.
    # Spotify requires an authenticated Web Playback session for full playback.
    PRIORITY = {"local": 110, "youtube": 100, "spotify": 90, "audius": 80, "jamendo": 75, "soundcloud": 70, "deezer": 30, "apple": 20}

    def __init__(self, db: Session):
        self.db = db

    def _preferred_provider(self, track_id: str) -> str | None:
        return None

    def _provider_connected(self, provider: str) -> bool:
        if provider == "local":
            return True
        # Public/embedded sources do not need an account session. The resolver
        # only gates providers whose playback API is explicitly session-bound.
        if provider == "youtube":
            return True
        if provider == "spotify":
            acc = self.db.scalar(select(IntegrationAccount).where(IntegrationAccount.provider == provider))
            return bool(acc and acc.access_token)
        # A provider-specific source is already expected to be a playable URI.
        return True

    def resolve(self, track_id: str, preferred_provider: str | None = None) -> PlaybackResolution:
        track = self.db.get(Track, track_id)
        if not track:
            return PlaybackResolution(False, track_id=track_id, reason="track_not_found", candidates=[])
        all_sources = list(self.db.scalars(select(TrackSource).where(TrackSource.track_id == track_id, TrackSource.available.is_(True))))
        if not all_sources:
            return PlaybackResolution(False, track_id=track_id, reason="no_playback_source", candidates=[])

        playable = [s for s in all_sources if self._provider_connected(s.provider)]
        candidates = []
        for s in all_sources:
            candidates.append({
                "provider": s.provider,
                "provider_id": s.provider_id,
                "kind": s.playback_kind or "external",
                "source": s.provider_id if s.provider == "youtube" else (s.uri or s.provider_id),
                "available": s in playable,
                "reason": None if s in playable else "provider_not_connected",
            })
        if not playable:
            return PlaybackResolution(False, track_id=track_id, candidates=candidates, reason="provider_not_connected")

        preferred = preferred_provider or self._preferred_provider(track_id)
        playable.sort(key=lambda s: (0 if preferred and s.provider == preferred else 1, -self.PRIORITY.get(s.provider, 0)))
        selected = playable[0]
        source = selected.provider_id if selected.provider == "youtube" else (selected.uri or selected.provider_id)
        return PlaybackResolution(True, provider=selected.provider, kind=selected.playback_kind or "external", source=source, track_id=track_id, candidates=candidates)
