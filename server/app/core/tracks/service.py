from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Album, Artist, Track, TrackSource
from app.providers.base.provider import ProviderTrack
from app.services.identity.matcher import normalize_text, track_match_score


def _get_or_create_artist(db: Session, name: str) -> Artist | None:
    if not name:
        return None
    norm = normalize_text(name)
    artist = db.scalar(select(Artist).where(Artist.normalized_name == norm))
    if not artist:
        artist = Artist(name=name.strip(), normalized_name=norm)
        db.add(artist)
        db.flush()
    return artist


def _get_or_create_album(db: Session, title: str, artist_id: str | None) -> Album | None:
    if not title:
        return None
    album = db.scalar(select(Album).where(Album.title == title, Album.artist_id == artist_id))
    if not album:
        album = Album(title=title.strip(), artist_id=artist_id)
        db.add(album)
        db.flush()
    return album


def find_canonical_match(db: Session, item: ProviderTrack, threshold: float = 0.86) -> Track | None:
    isrc = (item.metadata or {}).get("isrc")
    if isrc:
        exact = db.scalar(select(Track).where(Track.isrc == isrc))
        if exact:
            return exact

    title_norm = normalize_text(item.title)
    artist_norm = normalize_text(item.artist)
    if not title_norm:
        return None

    stmt = select(Track).where(Track.normalized_title == title_norm)
    candidates = list(db.scalars(stmt).all())
    if not candidates and artist_norm:
        # Narrow candidate search by artist text when title normalization differs.
        artist = db.scalar(select(Artist).where(Artist.normalized_name == artist_norm))
        if artist:
            candidates = list(db.scalars(select(Track).where(Track.artist_id == artist.id)).all())

    best: tuple[float, Track] | None = None
    for candidate in candidates:
        candidate_artist = db.get(Artist, candidate.artist_id) if candidate.artist_id else None
        score = track_match_score(
            item.title,
            item.artist,
            item.duration_ms,
            candidate.title,
            candidate_artist.name if candidate_artist else "",
            candidate.duration_ms,
            isrc,
            candidate.isrc,
        )
        if best is None or score > best[0]:
            best = (score, candidate)
    return best[1] if best and best[0] >= threshold else None


def upsert_provider_track(db: Session, item: ProviderTrack) -> Track:
    source = db.scalar(
        select(TrackSource).where(
            TrackSource.provider == item.provider,
            TrackSource.provider_id == item.provider_id,
        )
    )
    if source:
        track = db.get(Track, source.track_id)
        if track:
            _refresh_track(db, track, item, source)
            db.commit()
            db.refresh(track)
            return track

    track = find_canonical_match(db, item)
    if track:
        artist = db.get(Artist, track.artist_id) if track.artist_id else None
        album = db.get(Album, track.album_id) if track.album_id else None
        source = TrackSource(
            track_id=track.id,
            provider=item.provider,
            provider_id=item.provider_id,
            uri=item.uri,
            playback_kind=(item.metadata or {}).get("playback_kind", "external"),
            available=True,
        )
        db.add(source)
        if artist and not track.artwork_url and item.artwork_url:
            track.artwork_url = item.artwork_url
        if album and item.album and not album.title:
            album.title = item.album
        db.commit()
        db.refresh(track)
        return track

    artist = _get_or_create_artist(db, item.artist)
    album = _get_or_create_album(db, item.album, artist.id if artist else None)
    track = Track(
        title=item.title.strip() or "Unknown",
        normalized_title=normalize_text(item.title),
        artist_id=artist.id if artist else None,
        album_id=album.id if album else None,
        duration_ms=item.duration_ms,
        artwork_url=item.artwork_url,
        isrc=(item.metadata or {}).get("isrc"),
    )
    db.add(track)
    db.flush()
    db.add(
        TrackSource(
            track_id=track.id,
            provider=item.provider,
            provider_id=item.provider_id,
            uri=item.uri,
            playback_kind=(item.metadata or {}).get("playback_kind", "external"),
            available=True,
        )
    )
    db.commit()
    db.refresh(track)
    return track


def _refresh_track(db: Session, track: Track, item: ProviderTrack, source: TrackSource) -> None:
    if not track.title and item.title:
        track.title = item.title
    if item.duration_ms and (not track.duration_ms or abs(track.duration_ms - item.duration_ms) < 10000):
        track.duration_ms = item.duration_ms
    if item.artwork_url and not track.artwork_url:
        track.artwork_url = item.artwork_url
    if item.metadata.get("isrc") and not track.isrc:
        track.isrc = item.metadata["isrc"]
    source.uri = item.uri or source.uri
    source.playback_kind = item.metadata.get("playback_kind", source.playback_kind or "external")
    source.available = True
