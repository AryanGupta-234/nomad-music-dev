from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.db.models import PlayerState, PlayerQueueItem


def now(): return datetime.now(timezone.utc)

@dataclass
class QueueState:
    profile_id: str
    current_item_id: str | None
    is_playing: bool
    position_ms: int
    volume: float
    shuffle: bool
    repeat: str
    items: list[dict]

class QueueService:
    def __init__(self, db: Session): self.db = db

    def _state(self, profile_id: str) -> PlayerState:
        state = self.db.scalar(select(PlayerState).where(PlayerState.profile_id == profile_id))
        if not state:
            state = PlayerState(profile_id=profile_id)
            self.db.add(state); self.db.commit(); self.db.refresh(state)
        return state

    def get(self, profile_id: str) -> QueueState:
        s = self._state(profile_id)
        rows = self.db.scalars(select(PlayerQueueItem).where(PlayerQueueItem.profile_id == profile_id).order_by(PlayerQueueItem.position)).all()
        return QueueState(profile_id, s.current_item_id, s.is_playing, s.position_ms, s.volume, s.shuffle, s.repeat,
                          [{"id": r.id, "track_id": r.track_id, "position": r.position, "source": r.preferred_source} for r in rows])

    def replace(self, profile_id: str, track_ids: list[str], start_index: int = 0) -> QueueState:
        self._state(profile_id)
        self.db.execute(delete(PlayerQueueItem).where(PlayerQueueItem.profile_id == profile_id))
        for pos, track_id in enumerate(track_ids):
            self.db.add(PlayerQueueItem(profile_id=profile_id, track_id=track_id, position=pos))
        self.db.flush()
        rows = self.db.scalars(select(PlayerQueueItem).where(PlayerQueueItem.profile_id == profile_id).order_by(PlayerQueueItem.position)).all()
        s = self._state(profile_id)
        s.current_item_id = rows[start_index].id if rows and 0 <= start_index < len(rows) else (rows[0].id if rows else None)
        s.updated_at = now()
        s.position_ms = 0
        s.is_playing = False
        self.db.commit()
        return self.get(profile_id)

    def set_state(self, profile_id: str, **kwargs) -> QueueState:
        s = self._state(profile_id)
        allowed = {"current_item_id", "is_playing", "position_ms", "volume", "shuffle", "repeat"}
        for k, v in kwargs.items():
            if k in allowed and v is not None: setattr(s, k, v)
        self.db.commit()
        return self.get(profile_id)

    def next(self, profile_id: str) -> QueueState:
        state = self.get(profile_id)
        if not state.items: return state
        idx = next((i for i, x in enumerate(state.items) if x["id"] == state.current_item_id), -1)
        if idx < 0: return self.set_state(profile_id, current_item_id=state.items[0]["id"], position_ms=0)
        if idx + 1 >= len(state.items):
            if state.repeat == "all":
                return self.set_state(profile_id, current_item_id=state.items[0]["id"], position_ms=0)
            return self.set_state(profile_id, is_playing=False, position_ms=0)
        return self.set_state(profile_id, current_item_id=state.items[idx + 1]["id"], position_ms=0)

    def previous(self, profile_id: str) -> QueueState:
        state = self.get(profile_id)
        if not state.items: return state
        idx = next((i for i, x in enumerate(state.items) if x["id"] == state.current_item_id), 0)
        if idx <= 0:
            if state.repeat == "all": idx = len(state.items) - 1
            else: idx = 0
        else: idx -= 1
        return self.set_state(profile_id, current_item_id=state.items[idx]["id"], position_ms=0)


    def smart_extend(self, profile_id: str, count: int = 5, exclude_current: bool = True) -> QueueState:
        """Append recommendation-ranked tracks while keeping queue uniqueness."""
        from app.services.recommendations.service import recommend
        recs = recommend(self.db, profile_id, limit=max(count * 4, count))
        existing = {item["track_id"] for item in self.get(profile_id).items}
        current = self.get(profile_id).current_item_id
        chosen = []
        for candidate, _score in recs:
            if candidate.track_id in existing or (exclude_current and candidate.track_id == current):
                continue
            chosen.append(candidate.track_id)
            existing.add(candidate.track_id)
            if len(chosen) >= count:
                break
        state = self.get(profile_id)
        start = len(state.items)
        for idx, track_id in enumerate(chosen, start=start):
            self.db.add(PlayerQueueItem(profile_id=profile_id, track_id=track_id, position=idx))
        self.db.commit()
        return self.get(profile_id)
