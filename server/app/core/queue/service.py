from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import random
from sqlalchemy import select, delete
from sqlalchemy.orm import Session
from app.db.models import PlayerState, PlayerQueueItem
from app.core.profiles.service import get_or_create_default


def now():
    return datetime.now(timezone.utc)


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
    def __init__(self, db: Session):
        self.db = db

    def _profile_id(self, profile_id: str | None) -> str:
        """Resolve the API's legacy 'default' alias to the real default profile id."""
        if profile_id and profile_id != "default":
            return profile_id
        return get_or_create_default(self.db).id

    def _state(self, profile_id: str) -> PlayerState:
        profile_id = self._profile_id(profile_id)
        state = self.db.scalar(select(PlayerState).where(PlayerState.profile_id == profile_id))
        if not state:
            state = PlayerState(profile_id=profile_id)
            self.db.add(state)
            self.db.commit()
            self.db.refresh(state)
        return state

    def get(self, profile_id: str | None) -> QueueState:
        profile_id = self._profile_id(profile_id)
        s = self._state(profile_id)
        rows = self.db.scalars(
            select(PlayerQueueItem)
            .where(PlayerQueueItem.profile_id == profile_id)
            .order_by(PlayerQueueItem.position)
        ).all()
        return QueueState(
            profile_id,
            s.current_item_id,
            s.is_playing,
            s.position_ms,
            s.volume,
            s.shuffle,
            s.repeat,
            [
                {"id": r.id, "track_id": r.track_id, "position": r.position, "source": r.preferred_source}
                for r in rows
            ],
        )

    def replace(self, profile_id: str | None, track_ids: list[str], start_index: int = 0) -> QueueState:
        profile_id = self._profile_id(profile_id)
        self._state(profile_id)
        self.db.execute(delete(PlayerQueueItem).where(PlayerQueueItem.profile_id == profile_id))
        for pos, track_id in enumerate(track_ids):
            self.db.add(PlayerQueueItem(profile_id=profile_id, track_id=track_id, position=pos))
        self.db.flush()
        rows = self.db.scalars(
            select(PlayerQueueItem)
            .where(PlayerQueueItem.profile_id == profile_id)
            .order_by(PlayerQueueItem.position)
        ).all()
        s = self._state(profile_id)
        s.current_item_id = rows[start_index].id if rows and 0 <= start_index < len(rows) else (rows[0].id if rows else None)
        s.updated_at = now()
        s.position_ms = 0
        s.is_playing = False
        self.db.commit()
        return self.get(profile_id)

    def set_state(self, profile_id: str | None, **kwargs) -> QueueState:
        profile_id = self._profile_id(profile_id)
        s = self._state(profile_id)
        allowed = {"current_item_id", "is_playing", "position_ms", "volume", "shuffle", "repeat"}
        for k, v in kwargs.items():
            if k in allowed and v is not None:
                setattr(s, k, v)
        self.db.commit()
        return self.get(profile_id)

    def _pick_shuffle(self, state: QueueState, current_index: int) -> dict | None:
        candidates = [item for i, item in enumerate(state.items) if i != current_index]
        if not candidates:
            return None
        return random.SystemRandom().choice(candidates)

    def next(self, profile_id: str | None) -> QueueState:
        state = self.get(profile_id)
        if not state.items:
            return state

        idx = next((i for i, x in enumerate(state.items) if x["id"] == state.current_item_id), -1)
        if idx < 0:
            return self.set_state(profile_id, current_item_id=state.items[0]["id"], position_ms=0)

        # Repeat-one intentionally wins over shuffle/repeat-all: the current item
        # must be replayed without changing queue order.
        if state.repeat == "one":
            return self.set_state(profile_id, current_item_id=state.items[idx]["id"], position_ms=0, is_playing=True)

        if state.shuffle:
            candidate = self._pick_shuffle(state, idx)
            if candidate:
                return self.set_state(profile_id, current_item_id=candidate["id"], position_ms=0)

        if idx + 1 >= len(state.items):
            if state.repeat == "all":
                return self.set_state(profile_id, current_item_id=state.items[0]["id"], position_ms=0)
            return self.set_state(profile_id, is_playing=False, position_ms=0)
        return self.set_state(profile_id, current_item_id=state.items[idx + 1]["id"], position_ms=0)

    def previous(self, profile_id: str | None) -> QueueState:
        state = self.get(profile_id)
        if not state.items:
            return state
        idx = next((i for i, x in enumerate(state.items) if x["id"] == state.current_item_id), 0)

        if state.shuffle and len(state.items) > 1:
            candidate = self._pick_shuffle(state, idx)
            if candidate:
                return self.set_state(profile_id, current_item_id=candidate["id"], position_ms=0)

        if idx <= 0:
            if state.repeat == "all":
                idx = len(state.items) - 1
            else:
                idx = 0
        else:
            idx -= 1
        return self.set_state(profile_id, current_item_id=state.items[idx]["id"], position_ms=0)

    def smart_extend(self, profile_id: str | None, count: int = 5, exclude_current: bool = True) -> QueueState:
        """Append recommendation-ranked tracks while keeping queue uniqueness."""
        from app.services.recommendations.service import recommend
        profile_id = self._profile_id(profile_id)
        recs = recommend(self.db, profile_id, limit=max(count * 4, count))
        state = self.get(profile_id)
        existing = {item["track_id"] for item in state.items}
        current = next((item["track_id"] for item in state.items if item["id"] == state.current_item_id), None)
        chosen = []
        for candidate, _score in recs:
            if candidate.track_id in existing or (exclude_current and candidate.track_id == current):
                continue
            chosen.append(candidate.track_id)
            existing.add(candidate.track_id)
            if len(chosen) >= count:
                break
        start = len(state.items)
        for idx, track_id in enumerate(chosen, start=start):
            self.db.add(PlayerQueueItem(profile_id=profile_id, track_id=track_id, position=idx))
        self.db.commit()
        return self.get(profile_id)
