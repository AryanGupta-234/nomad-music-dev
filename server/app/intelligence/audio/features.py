from __future__ import annotations
import json, re, subprocess
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Track, Artist, AudioFeature, TrackSource

ENERGY_WORDS = {"high": ["banger","energy","workout","hype","party","dance","upbeat","hard"],
                "low": ["sleep","ambient","calm","acoustic","piano","rain","soft","sad"],
                "dark": ["dark","night","midnight","after dark","moody","shadow"]}

def _mood(text: str, energy: float) -> str:
    low = text.lower()
    for mood, words in ENERGY_WORDS.items():
        if any(w in low for w in words):
            return mood
    return "energetic" if energy >= .72 else "balanced" if energy >= .42 else "calm"

def _duration_seconds(track: Track) -> float:
    return max(0, (track.duration_ms or 0) / 1000.0)

def analyze_track(db: Session, track_id: str, force: bool = False) -> AudioFeature | None:
    track = db.get(Track, track_id)
    if not track:
        return None
    existing = db.scalar(select(AudioFeature).where(AudioFeature.track_id == track_id))
    if existing and not force:
        return existing
    artist = db.get(Artist, track.artist_id) if track.artist_id else None
    text = f"{track.title} {artist.name if artist else ''}"
    duration = _duration_seconds(track)
    # Lightweight always-available baseline. A heavier librosa pass can overwrite this later.
    energy = 0.68 if any(w in text.lower() for w in ENERGY_WORDS["high"]) else 0.28 if any(w in text.lower() for w in ENERGY_WORDS["low"]) else 0.5
    dance = min(1.0, max(0.0, energy * 0.88 + 0.18))
    acoustic = 0.72 if any(w in text.lower() for w in ["acoustic","piano","folk","unplugged"]) else 0.22 if any(w in text.lower() for w in ["electronic","edm","club","synth","techno"]) else 0.45
    bpm = 128.0 if energy > .65 else 92.0 if energy < .35 else 110.0

    # Optional real local-file extraction when librosa is installed and a local_audio source exists.
    local = db.scalar(select(TrackSource).where(TrackSource.track_id == track_id, TrackSource.playback_kind == "local_audio"))
    if local and local.uri:
        path = local.uri.replace("file://", "", 1)
        try:
            import librosa  # optional heavy dependency
            y, sr = librosa.load(Path(path), sr=22050, mono=True)
            if y.size:
                tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
                bpm = float(tempo if not hasattr(tempo, "__len__") else tempo[0])
                rms = float(librosa.feature.rms(y=y).mean())
                energy = max(0.0, min(1.0, rms * 8.0))
                dance = max(0.0, min(1.0, energy * .55 + .32))
                acoustic = max(0.0, min(1.0, 1.0 - energy * .55))
        except Exception:
            pass

    data = {"bpm": round(bpm, 1), "energy": round(energy, 3), "danceability": round(dance, 3), "acousticness": round(acoustic, 3), "duration": round(duration, 2)}
    row = existing or AudioFeature(track_id=track_id)
    row.model_version = "metadata-v1"
    row.bpm = data["bpm"]
    row.energy = data["energy"]
    row.danceability = data["danceability"]
    row.acousticness = data["acousticness"]
    row.mood = _mood(text, energy)
    row.source = "librosa" if local else "metadata"
    row.raw_json = json.dumps(data)
    db.add(row); db.commit(); db.refresh(row)
    return row
