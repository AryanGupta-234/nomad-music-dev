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
    PRIORITY = {"local": 100, "spotify": 90, "audius": 70, "jamendo": 65, "youtube": 50, "deezer": 30, "apple": 20}

    def __init__(self, db: Session):
        self.db = db

    def _preferred_provider(self, track_id: str) -> str | None:
        return None

    def _provider_connected(self, provider: str) -> bool:
        """Return whether a provider has an authenticated local session.

        Public provider metadata can exist without an authenticated account. A
        playback resolver must not select such a source and then make the UI
        discover the failure only after playback has already started.
        """
        if provider == "local":
            return True
        if provider not in {"spotify", "youtube"}:
            return True
        acc = self.db.scalar(
            select(IntegrationAccount).where(IntegrationAccount.provider == provider)
        )
        return bool(acc and acc.access_token)

    def resolve(self, track_id: str, preferred_provider: str | None = None) -> PlaybackResolution:
        track = self.db.get(Track, track_id)
        if not track:
            return PlaybackResolution(False, track_id=track_id, reason="track_not_found", candidates=[])

        all_sources = list(
            self.db.scalars(
                select(TrackSource).where(
                    TrackSource.track_id == track_id,
                    TrackSource.available.is_(True),
                )
            )
        )
        if not all_sources:
            return PlaybackResolution(False, track_id=track_id, reason="no_playback_source", candidates=[])

        # Keep disconnected authenticated-provider sources as diagnostic
        # candidates, but never select them as the active playback source.
        playable = [s for s in all_sources if self._provider_connected(s.provider)]
        if not playable:
            candidates = [
                {
                    "provider": s.provider,
                    "provider_id": s.provider_id,
                    "kind": s.playback_kind or "external",
                    "source": s.provider_id if s.provider == "youtube" else (s.uri or s.provider_id),
                    "available": False,
                    "reason": "provider_not_connected",
                }
                for s in all_sources
            ]
            return PlaybackResolution(
                False,
                track_id=track_id,
                candidates=candidates,
                reason="provider_not_connected",
            )

        preferred = preferred_provider or self._preferred_provider(track_id)
        if preferred:
            playable.sort(
                key=lambda s: (
                    0 if s.provider == preferred else 1,
                    -self.PRIORITY.get(s.provider, 0),
                )
            )
        else:
            playable.sort(key=lambda s: self.PRIORITY.get(s.provider, 0), reverse=True)

        def source_value(s: TrackSource) -> str:
            if s.provider == "youtube":
                return s.provider_id
            return s.uri or s.provider_id

        candidates = [
            {
                "provider": s.provider,
                "provider_id": s.provider_id,
                "kind": s.playback_kind or "external",
                "source": source_value(s),
                "available": True,
            }
            for s in playable
        ]
        selected = playable[0]
        return PlaybackResolution(
            True,
            provider=selected.provider,
            kind=selected.playback_kind or "external",
            source=source_value(selected),
            track_id=track_id,
            candidates=candidates,
        )
