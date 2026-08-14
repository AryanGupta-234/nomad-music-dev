from __future__ import annotations
from pathlib import Path
from typing import Iterable
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.models import Track, TrackSource, Artist, Album
from app.services.identity.matcher import normalize_text

AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".wav", ".ogg", ".opus", ".aac", ".alac", ".wma"}

def _meta(path: Path) -> dict:
    title = path.stem
    artist = ""
    album = ""
    duration_ms = None
    artwork_url = None
    try:
        from mutagen import File
        f = File(path, easy=True)
        if f:
            title = (f.get("title", [title]) or [title])[0]
            artist = (f.get("artist", [""]) or [""])[0]
            album = (f.get("album", [""]) or [""])[0]
            if getattr(f, "info", None) and getattr(f.info, "length", None):
                duration_ms = int(float(f.info.length) * 1000)
    except Exception:
        pass
    return {"title": title.strip() or path.stem, "artist": artist.strip(), "album": album.strip(), "duration_ms": duration_ms, "artwork_url": artwork_url}

def _artist(db: Session, name: str) -> Artist | None:
    if not name:
        return None
    n = normalize_text(name)
    a = db.scalar(select(Artist).where(Artist.normalized_name == n))
    if not a:
        a = Artist(name=name, normalized_name=n); db.add(a); db.flush()
    return a

def _album(db: Session, title: str, artist_id: str | None) -> Album | None:
    if not title:
        return None
    a = db.scalar(select(Album).where(Album.title == title, Album.artist_id == artist_id))
    if not a:
        a = Album(title=title, artist_id=artist_id); db.add(a); db.flush()
    return a

def index_paths(db: Session, root: str, recursive: bool = True, limit: int = 500) -> dict:
    base = Path(root).expanduser().resolve()
    if not base.exists() or not base.is_dir():
        raise ValueError(f"library folder does not exist: {base}")
    paths: Iterable[Path] = base.rglob("*") if recursive else base.glob("*")
    scanned = indexed = skipped = 0
    for path in paths:
        if scanned >= max(1, min(limit, 5000)):
            break
        if not path.is_file() or path.suffix.lower() not in AUDIO_EXTS:
            continue
        scanned += 1
        existing = db.scalar(select(TrackSource).where(TrackSource.provider == "local", TrackSource.provider_id == str(path)))
        if existing:
            continue
        meta = _meta(path)
        a = _artist(db, meta["artist"])
        al = _album(db, meta["album"], a.id if a else None)
        track = Track(title=meta["title"], normalized_title=normalize_text(meta["title"]), artist_id=a.id if a else None,
                      album_id=al.id if al else None, duration_ms=meta["duration_ms"], artwork_url=meta["artwork_url"])
        db.add(track); db.flush()
        db.add(TrackSource(track_id=track.id, provider="local", provider_id=str(path), uri=str(path), playback_kind="local_audio", available=True))
        indexed += 1
    db.commit()
    return {"root": str(base), "scanned": scanned, "indexed": indexed, "skipped": skipped}
