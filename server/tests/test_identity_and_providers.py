from app.services.identity.matcher import track_match_score
from app.providers.deezer.provider import DeezerProvider


def test_isrc_is_exact_identity():
    assert track_match_score("A", "B", 200000, "Completely Different", "Other", 300000, "US-ABC-123", "us-abc-123") == 1.0


def test_title_artist_duration_similarity_is_strong_for_same_track():
    score = track_match_score("After Hours", "The Weeknd", 360000, "After Hours", "The Weeknd", 359000)
    assert score >= 0.95


def test_deezer_provider_is_available_without_credentials():
    provider = DeezerProvider()
    assert provider.name == "deezer"
