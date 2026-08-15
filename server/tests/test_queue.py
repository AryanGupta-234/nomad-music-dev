import os
os.environ["DATABASE_URL"] = "sqlite:///./test_queue.db"

from app.db.session import engine, SessionLocal
from app.db.models.base import Base
from app.db.models import Track, Profile
from app.core.queue.service import QueueService


def test_queue_roundtrip_and_repeat_all():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    p = Profile(name="Test", is_default=True)
    db.add(p)
    a = Track(title="A", normalized_title="a")
    b = Track(title="B", normalized_title="b")
    db.add_all([a, b])
    db.commit()
    db.refresh(p)
    db.refresh(a)
    db.refresh(b)

    svc = QueueService(db)
    q = svc.replace(p.id, [a.id, b.id])
    assert len(q.items) == 2
    q = svc.next(p.id)
    assert q.current_item_id == q.items[1]["id"]
    q = svc.set_state(p.id, is_playing=True, position_ms=1234, repeat="all")
    assert q.is_playing is True and q.position_ms == 1234
    q = svc.next(p.id)
    assert q.current_item_id == q.items[0]["id"]

    db.close()
    Base.metadata.drop_all(engine)


def test_queue_resolves_default_alias_and_repeat_one():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    p = Profile(name="Real Default", is_default=True)
    db.add(p)
    a = Track(title="A", normalized_title="a")
    b = Track(title="B", normalized_title="b")
    db.add_all([a, b])
    db.commit()

    svc = QueueService(db)
    q = svc.replace("default", [a.id, b.id])
    assert q.profile_id == p.id
    q = svc.set_state("default", repeat="one", is_playing=True)
    current = q.current_item_id
    q = svc.next("default")
    assert q.profile_id == p.id
    assert q.current_item_id == current
    assert q.position_ms == 0
    assert q.is_playing is True

    db.close()
    Base.metadata.drop_all(engine)


def test_queue_shuffle_changes_track_without_reordering_queue():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    p = Profile(name="Shuffle", is_default=True)
    db.add(p)
    tracks = [Track(title=letter, normalized_title=letter.lower()) for letter in "ABC"]
    db.add_all(tracks)
    db.commit()

    svc = QueueService(db)
    q = svc.replace(p.id, [t.id for t in tracks])
    q = svc.set_state(p.id, shuffle=True)
    current = q.current_item_id
    q = svc.next(p.id)
    assert q.current_item_id != current
    assert [item["track_id"] for item in q.items] == [t.id for t in tracks]

    db.close()
    Base.metadata.drop_all(engine)
