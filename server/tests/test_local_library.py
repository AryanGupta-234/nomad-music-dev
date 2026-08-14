from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.db.models.base import Base
from app.db.models import Track, TrackSource
from app.services.local_library import index_paths

def test_local_library_indexes_audio_file(tmp_path: Path):
    audio = tmp_path / "Test Song.mp3"
    audio.write_bytes(b"not-real-mp3")
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        result = index_paths(db, str(tmp_path))
        assert result["indexed"] == 1
        track = db.scalar(select(Track))
        assert track.title == "Test Song"
        source = db.scalar(select(TrackSource))
        assert source.provider == "local"
        assert source.playback_kind == "local_audio"
