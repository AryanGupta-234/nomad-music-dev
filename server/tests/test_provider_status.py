from app.providers.registry import provider_status

def test_spotify_status_uses_client_id_for_pkce(monkeypatch):
    from app.config.settings import Settings, get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("SPOTIFY_CLIENT_ID", "client-id")
    monkeypatch.delenv("SPOTIFY_CLIENT_SECRET", raising=False)
    rows = provider_status()
    spotify = next(x for x in rows if x["name"] == "spotify")
    assert spotify["configured"] is True
    assert spotify["mode"] == "pkce"
    assert spotify["client_secret_configured"] is False
