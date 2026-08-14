from app.config.settings import get_settings
from app.providers.apple.provider import AppleProvider
from app.providers.deezer.provider import DeezerProvider
from app.providers.mock.provider import MockMusicProvider
from app.providers.spotify.provider import SpotifyProvider
from app.providers.youtube.provider import YouTubeProvider


def music_providers():
    settings = get_settings()
    providers = [MockMusicProvider(), DeezerProvider(), AppleProvider()]
    if settings.spotify_client_id and settings.spotify_client_secret:
        providers.append(SpotifyProvider(settings.spotify_client_id, settings.spotify_client_secret))
    if settings.youtube_api_key:
        providers.append(YouTubeProvider(settings.youtube_api_key))
    return providers


def provider_status():
    settings = get_settings()
    return [
        {"name": "mock", "configured": True, "mode": "local"},
        {"name": "deezer", "configured": True, "mode": "public_metadata"},
        {"name": "apple", "configured": True, "mode": "public_metadata"},
        {
            "name": "spotify",
            "configured": bool(settings.spotify_client_id),
            "mode": "pkce",
            "client_id_configured": bool(settings.spotify_client_id),
            "client_secret_configured": bool(settings.spotify_client_secret),
            "search_mode": "user_session" if settings.spotify_client_id else "unavailable",
            "playback": "web_playback_sdk",
        },
        {
            "name": "youtube",
            "configured": bool(settings.youtube_api_key or (settings.youtube_client_id and settings.youtube_client_secret)),
            "mode": "data_api",
            "api_key_configured": bool(settings.youtube_api_key),
            "oauth_configured": bool(settings.youtube_client_id and settings.youtube_client_secret),
        },
    ]
