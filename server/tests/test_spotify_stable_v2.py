import os
os.environ["DATABASE_URL"] = "sqlite:///./test_spotify_v2.db"

from urllib.parse import urlparse, parse_qs
from app.db.models.base import Base
from app.db.session import engine, SessionLocal
from app.db.models import Profile, OAuthState
from app.providers.spotify.provider import SpotifyProvider
from app.services.integrations import authorize_url
from app.config.settings import get_settings


def _reset():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def test_spotify_search_clamps_to_ten(monkeypatch):
    provider = SpotifyProvider("client", "secret")
    captured = {}
    async def fake_request(path, params=None):
        captured.update(params or {})
        return {"tracks": {"items": []}}
    monkeypatch.setattr(provider, "_request", fake_request)
    import asyncio
    asyncio.run(provider.search("test", 50))
    assert captured["limit"] == 10


def test_spotify_authorize_uses_pkce():
    _reset()
    db = SessionLocal()
    p = Profile(name="Default", is_default=True)
    db.add(p); db.commit(); db.refresh(p)
    os.environ["SPOTIFY_CLIENT_ID"] = "test-client"
    os.environ["PUBLIC_BASE_URL"] = "http://127.0.0.1:8765"
    get_settings.cache_clear()
    url = authorize_url(db, "spotify", p.id)
    qs = parse_qs(urlparse(url).query)
    assert qs["client_id"] == ["test-client"]
    assert qs["code_challenge_method"] == ["S256"]
    assert "code_challenge" in qs
    state = qs["state"][0]
    row = db.query(OAuthState).filter_by(state=state).one()
    assert row.code_verifier
    db.close(); _reset()
