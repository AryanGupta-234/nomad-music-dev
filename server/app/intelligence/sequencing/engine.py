from __future__ import annotations
from math import inf


def _duration(row: dict) -> int:
    return int(row.get("duration_ms") or 0)


def sequence_tracks(track_rows: list[dict], target_minutes: int | None = None, start_energy: float | None = None,
                    end_energy: float | None = None, avoid_repeats: bool = True) -> list[dict]:
    """Greedy playlist sequencer using duration, energy trajectory and artist diversity.

    It is deliberately deterministic so UI and mobile clients can reproduce the same
    result from the server response without local recommendation logic.
    """
    rows = list(track_rows)
    if not rows:
        return []

    def energy(row: dict) -> float:
        v = row.get("energy")
        return float(v) if v is not None else 0.5

    def artist(row: dict) -> str:
        return str(row.get("artist") or row.get("artist_id") or "").strip().lower()

    target_ms = target_minutes * 60_000 if target_minutes else None
    if start_energy is None and end_energy is None:
        if not target_ms:
            return rows
        out, total = [], 0
        for row in rows:
            d = _duration(row)
            if out and d and total + d > target_ms:
                break
            out.append(row)
            total += d
        return out

    start = 0.5 if start_energy is None else float(start_energy)
    end = start if end_energy is None else float(end_energy)
    remaining = rows[:]
    out: list[dict] = []
    total = 0
    used_artists: dict[str, int] = {}

    while remaining:
        position = len(out) / max(1, len(rows) - 1)
        target = start + (end - start) * position
        best_idx = 0
        best_score = -inf
        for idx, row in enumerate(remaining):
            e_score = 1.0 - abs(energy(row) - target)
            a = artist(row)
            artist_penalty = min(0.35, used_artists.get(a, 0) * 0.18) if avoid_repeats else 0.0
            duration_penalty = 0.0
            d = _duration(row)
            if target_ms and out and total + d > target_ms:
                duration_penalty = 0.45
            score = e_score - artist_penalty - duration_penalty
            if score > best_score:
                best_score = score
                best_idx = idx

        row = remaining.pop(best_idx)
        d = _duration(row)
        if target_ms and out and d and total + d > target_ms:
            break
        out.append(row)
        total += d
        used_artists[artist(row)] = used_artists.get(artist(row), 0) + 1

    return out


def vibe_journey(track_rows: list[dict], stages: list[float] | None = None, target_minutes: int | None = None) -> list[dict]:
    stages = stages or [0.25, 0.45, 0.70, 0.90, 0.60]
    if not track_rows:
        return []
    buckets: list[list[dict]] = [[] for _ in stages]
    rows = sorted(track_rows, key=lambda r: float(r.get("energy") if r.get("energy") is not None else 0.5))
    for idx, row in enumerate(rows):
        bucket = min(len(stages) - 1, int(idx / max(1, len(rows)) * len(stages)))
        buckets[bucket].append(row)
    chosen = []
    for bucket in buckets:
        chosen.extend(bucket)
    return sequence_tracks(chosen, target_minutes=target_minutes, start_energy=stages[0], end_energy=stages[-1])
