import os
os.environ["DATABASE_URL"] = "sqlite:///./test_queue.db"
from app.db.session import engine, SessionLocal
from app.db.models.base import Base
from app.db.models import Track, Playlist, Profile
from app.core.queue.service import QueueService


def test_queue_roundtrip():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    db=SessionLocal()
    p=Profile(name="Test", is_default=True); db.add(p)
    a=Track(title="A", normalized_title="a"); b=Track(title="B", normalized_title="b")
    db.add_all([a,b]); db.commit(); db.refresh(p); db.refresh(a); db.refresh(b)
    svc=QueueService(db)
    q=svc.replace(p.id,[a.id,b.id]); assert len(q.items)==2
    q=svc.next(p.id); assert q.current_item_id == q.items[1]["id"]
    q=svc.set_state(p.id,is_playing=True,position_ms=1234,repeat="all"); assert q.is_playing is True and q.position_ms==1234
    q=svc.next(p.id); assert q.current_item_id==q.items[0]["id"]
    db.close(); Base.metadata.drop_all(engine)
