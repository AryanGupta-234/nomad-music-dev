from app.config.settings import get_settings
from app.providers.apple.provider import AppleProvider
from app.providers.audius.provider import AudiusProvider
from app.providers.deezer.provider import DeezerProvider
from app.providers.mock.provider import MockMusicProvider
from app.providers.spotify.provider import SpotifyProvider
from app.providers.youtube.provider import YouTubeProvider


def music_providers():
    settings = get_settings()
    # Audius needs no credentials at all - genuinely free, full-track,
    # no OAuth, no allowlist, no Premium requirement. Always available.
    providers = [MockMusicProvider(), DeezerProvider(), AppleProvider(), AudiusProvider()]

    # Spotify has two auth paths in NOMAD:
    # - authenticated desktop PKCE for the user's account/search/playback;
    # - client-credentials catalog search when a secret is configured.
    # Do not treat a missing client secret as a broken PKCE configuration.
    if settings.spotify_client_id and settings.spotify_client_secret:
        providers.append(SpotifyProvider(settings.spotify_client_id, settings.spotify_client_secret))

    # YouTube public catalog search uses the Data API key. OAuth-only accounts
    # are still valid for likes/playlists sync through integrations.py.
    if settings.youtube_api_key:
        providers.append(YouTubeProvider(settings.youtube_api_key))

    return providers


def provider_status():
    settings = get_settings()
    return [
        {"name": "mock", "configured": True, "mode": "local"},
        {"name": "deezer", "configured": True, "mode": "public_preview"},
        {"name": "apple", "configured": True, "mode": "public_preview"},
        {"name": "audius", "configured": True, "mode": "public_full_stream"},
        {
            "name": "spotify",
            # Client ID is sufficient to start the desktop PKCE flow. The
            # client secret is optional for PKCE, per the Stable v2 setup.
            "configured": bool(settings.spotify_client_id),
            "mode": "pkce",
            "client_id_configured": bool(settings.spotify_client_id),
            "client_secret_configured": bool(settings.spotify_client_secret),
            "pkce_ready": bool(settings.spotify_client_id),
            "catalog_client_credentials_ready": bool(settings.spotify_client_id and settings.spotify_client_secret),
            "search_mode": "user_session" if settings.spotify_client_id else "unavailable",
            "playback": "web_playback_sdk",
        },
        {
            "name": "youtube",
            "configured": bool(settings.youtube_api_key or (settings.youtube_client_id and settings.youtube_client_secret)),
            "mode": "data_api",
            "api_key_configured": bool(settings.youtube_api_key),
            "oauth_configured": bool(settings.youtube_client_id and settings.youtube_client_secret),
            "oauth_ready": bool(settings.youtube_client_id and settings.youtube_client_secret),
            "catalog_search_ready": bool(settings.youtube_api_key),
        },
    ]
