import re
from app.schemas.music import VibeQuery

def parse_vibe(text: str) -> VibeQuery:
    q = text.strip()
    low = q.lower()
    energy = None
    if any(w in low for w in ("high energy", "workout", "hype", "aggressive")):
        energy = 0.85
    elif any(w in low for w in ("calm", "chill", "sleep", "ambient")):
        energy = 0.25
    elif any(w in low for w in ("coding", "focus", "study", "work")):
        energy = 0.45
    familiarity = 0.5
    if any(w in low for w in ("discover", "new music", "hidden gems", "something new")):
        familiarity = 0.2
    elif any(w in low for w in ("familiar", "favorites", "my usual")):
        familiarity = 0.8
    duration = None
    m = re.search(r"(\d+)\s*(?:minute|min|mins)", low)
    if m:
        duration = max(5, min(360, int(m.group(1))))
    return VibeQuery(query=q, duration_minutes=duration, familiarity=familiarity, energy=energy)
