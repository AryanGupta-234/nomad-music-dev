import os
os.environ["DATABASE_URL"] = "sqlite:///./test_radio.db"
from app.db.session import engine, SessionLocal
from app.db.models.base import Base
from app.db.models import Profile, Track, TrackSource
from app.core.playback.resolver import PlaybackResolver
from app.intelligence.sequencing.engine import vibe_journey


def reset():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_resolver_prefers_requested_provider():
    reset(); db=SessionLocal()
    p=Profile(name="p",is_default=True); db.add(p)
    t=Track(title="A",normalized_title="a"); db.add(t); db.flush()
    db.add(TrackSource(track_id=t.id, provider="spotify", provider_id="sp1", uri="spotify:track:sp1", playback_kind="spotify_sdk"))
    db.add(TrackSource(track_id=t.id, provider="youtube", provider_id="yt1", uri="https://youtube.com/watch?v=yt1", playback_kind="youtube_external"))
    db.commit()
    r=PlaybackResolver(db).resolve(t.id, preferred_provider="youtube")
    assert r.provider == "youtube"
    assert r.candidates and len(r.candidates) == 2
    db.close(); reset()


def test_vibe_journey_orders_low_to_high_to_cooldown():
    rows=[{"id":str(i),"duration_ms":60_000,"energy":e,"artist":f"a{i}"} for i,e in enumerate([.1,.25,.4,.65,.8,.95,.7,.5,.3])]
    out=vibe_journey(rows, target_minutes=10)
    energies=[x["energy"] for x in out]
    assert energies
    assert max(energies) >= .9
    assert energies[-1] <= max(energies)
