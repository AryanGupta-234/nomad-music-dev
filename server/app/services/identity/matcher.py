from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").lower()
    value = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", value)
    value = re.sub(r"\b(feat|ft|featuring)\b.*$", " ", value)
    value = re.sub(r"[^\w\s]", " ", value, flags=re.UNICODE)
    return " ".join(value.split())


def similarity(a: str, b: str) -> float:
    a, b = normalize_text(a), normalize_text(b)
    return SequenceMatcher(None, a, b).ratio() if a and b else 0.0


def duration_similarity(duration_a: int | None, duration_b: int | None) -> float:
    if not duration_a or not duration_b:
        return 0.0
    delta = abs(duration_a - duration_b)
    if delta <= 1000:
        return 1.0
    if delta <= 2500:
        return 0.8
    if delta <= 5000:
        return 0.45
    if delta <= 10000:
        return 0.15
    return 0.0


def track_match_score(
    title_a: str,
    artist_a: str,
    duration_a: int | None,
    title_b: str,
    artist_b: str,
    duration_b: int | None,
    isrc_a: str | None = None,
    isrc_b: str | None = None,
) -> float:
    if isrc_a and isrc_b and isrc_a.strip().lower() == isrc_b.strip().lower():
        return 1.0
    title_score = similarity(title_a, title_b)
    artist_score = similarity(artist_a, artist_b)
    duration_score = duration_similarity(duration_a, duration_b)
    score = title_score * 0.58 + artist_score * 0.32 + duration_score * 0.10
    return round(min(1.0, score), 4)
