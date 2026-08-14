from app.intelligence.vibe.parser import parse_vibe

def test_vibe_parser():
    q=parse_vibe("dark late night coding playlist 60 minutes")
    assert q.duration_minutes == 60
    assert q.energy is not None
