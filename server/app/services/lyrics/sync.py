from __future__ import annotations
import re
from dataclasses import dataclass

_TAG_RE = re.compile(r"\[(\d{1,3}):(\d{2})(?:\.(\d{1,3}))?\]")

@dataclass(frozen=True)
class LyricLine:
    time_ms: int
    text: str

def parse_lrc(text: str | None) -> list[LyricLine]:
    if not text:
        return []
    rows: list[LyricLine] = []
    for raw in text.splitlines():
        matches = list(_TAG_RE.finditer(raw))
        if not matches:
            continue
        lyric = _TAG_RE.sub("", raw).strip()
        for m in matches:
            minutes = int(m.group(1))
            seconds = int(m.group(2))
            fraction = (m.group(3) or "")
            millis = int((fraction + "00")[:3])
            rows.append(LyricLine(minutes * 60000 + seconds * 1000 + millis, lyric))
    rows.sort(key=lambda x: x.time_ms)
    return rows

def active_index(lines: list[LyricLine], position_ms: int, offset_ms: int = 0) -> int:
    target = position_ms + offset_ms
    lo, hi = 0, len(lines) - 1
    best = -1
    while lo <= hi:
        mid = (lo + hi) // 2
        if lines[mid].time_ms <= target:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best
