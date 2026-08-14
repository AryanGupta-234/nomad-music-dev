
import os
os.environ["DATABASE_URL"] = "sqlite:///./test_sync_queue.db"

import asyncio
from datetime import datetime, timezone
from sqlalchemy import select

from app.db.session import engine, SessionLocal
from app.db.models.base import Base
from app.db.models import Profile, Playlist, ExternalCollection, Track, UserSignal
from app.services import integrations
from app.providers.base.provider import ProviderTrack
from app.core.queue.service import QueueService


def _reset():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_smart_queue_extends_without_duplicates():
    _reset()
    db = SessionLocal()
    p = Profile(name="Smart", is_default=True)
    db.add(p)
    tracks=[]
    for i in range(6):
        t=Track(title=f"Track {i}", normalized_title=f"track {i}")
        db.add(t); tracks.append(t)
    db.commit(); db.refresh(p)
    db.add(UserSignal(profile_id=p.id, track_id=tracks[0].id, signal="like", value=2))
    db.commit()
    svc=QueueService(db)
    svc.replace(p.id,[tracks[0].id])
    state=svc.smart_extend(p.id, count=3)
    ids=[x["track_id"] for x in state.items]
    assert ids[0] == tracks[0].id
    assert len(ids) == 4
    assert len(set(ids)) == 4
    db.close(); _reset()


def test_reconcile_external_collection(monkeypatch):
    _reset()
    db=SessionLocal(); p=Profile(name="Sync", is_default=True); db.add(p); db.commit(); db.refresh(p)

    async def fake_get(db2, provider, profile_id, url, params=None):
        if provider == "spotify" and url.endswith('/me/tracks'):
            return {"items":[{"track":{"id":"sp1","type":"track","name":"Song A","duration_ms":180000,"artists":[{"name":"Artist"}],"album":{"name":"Album","images":[]},"external_ids":{"isrc":"X1"}}}],"total":1}
        if provider == "spotify" and url.endswith('/me/playlists'):
            return {"items":[],"total":0}
        raise AssertionError(url)
    monkeypatch.setattr(integrations, "_oauth_get", fake_get)
    result=asyncio.run(integrations.spotify_library(db, p.id, page_limit=50))
    assert result["imported_tracks"] == 1
    mapping=db.scalar(select(ExternalCollection).where(ExternalCollection.provider=="spotify", ExternalCollection.profile_id==p.id))
    assert mapping is not None
    playlist=db.get(Playlist, mapping.local_playlist_id)
    assert playlist is not None
    assert playlist.name.startswith("Spotify ·")
    assert db.scalar(select(Track).where(Track.isrc=="X1")) is not None
    db.close(); _reset()
