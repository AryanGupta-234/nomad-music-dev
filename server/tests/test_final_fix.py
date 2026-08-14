from pathlib import Path
import os

def test_env_example_uses_local_oauth_port():
    text = Path(Path(__file__).parents[2] / '.env.example').read_text()
    assert 'PUBLIC_BASE_URL=http://127.0.0.1:8765' in text

def test_youtube_resolver_uses_video_id():
    from app.db.session import SessionLocal
    from app.db.models import Track, TrackSource
    from app.core.playback.resolver import PlaybackResolver
    db = SessionLocal()
    try:
        t = Track(title='YT Test', normalized_title='yt test')
        db.add(t); db.flush()
        db.add(TrackSource(track_id=t.id, provider='youtube', provider_id='abc123', uri='https://www.youtube.com/watch?v=abc123', playback_kind='youtube_external', available=True))
        db.commit()
        r = PlaybackResolver(db).resolve(t.id)
        assert r.provider == 'youtube'
        assert r.source == 'abc123'
    finally:
        db.close()
