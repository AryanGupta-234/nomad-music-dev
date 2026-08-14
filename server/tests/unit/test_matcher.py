from app.services.identity.matcher import similarity, track_match_score

def test_similarity_handles_unicode():
    assert similarity("BTS - 봄날", "BTS 봄날") > 0.7

def test_track_match_is_high_for_same_song():
    score = track_match_score("Song", "Artist", 200000, "Song", "Artist", 201000)
    assert score >= 0.95
