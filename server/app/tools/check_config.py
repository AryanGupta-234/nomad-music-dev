"""Safe local provider configuration diagnostic.

Run from the repository root with:
    python -m app.tools.check_config

Run from `server/` with:
    python -m app.tools.check_config

Never prints secret values; only whether each required value is present.
"""
from app.config.settings import get_settings
from app.providers.registry import provider_status


def main() -> None:
    settings = get_settings()
    print("NOMAD provider configuration")
    print("=" * 34)
    print(f"PUBLIC_BASE_URL: {settings.public_base_url}")
    print(f"Spotify client ID:     {'FOUND' if settings.spotify_client_id else 'MISSING'}")
    print(f"Spotify client secret: {'FOUND' if settings.spotify_client_secret else 'MISSING (OK for PKCE)'}")
    print(f"YouTube client ID:     {'FOUND' if settings.youtube_client_id else 'MISSING'}")
    print(f"YouTube client secret: {'FOUND' if settings.youtube_client_secret else 'MISSING'}")
    print(f"YouTube API key:       {'FOUND' if settings.youtube_api_key else 'MISSING'}")
    print()
    print("Provider capability status")
    print("=" * 34)
    for row in provider_status():
        print(f"{row['name']}: configured={row.get('configured')} mode={row.get('mode')}")
        for key in (
            "pkce_ready",
            "catalog_client_credentials_ready",
            "catalog_search_ready",
            "oauth_ready",
            "client_id_configured",
            "client_secret_configured",
            "api_key_configured",
            "oauth_configured",
        ):
            if key in row:
                print(f"  {key}: {row[key]}")
    print()
    print("OAuth callbacks")
    print(f"Spotify: {settings.public_base_url.rstrip('/')}/api/v1/integrations/spotify/callback")
    print(f"YouTube: {settings.public_base_url.rstrip('/')}/api/v1/integrations/youtube/callback")
    print()
    print("If you changed .env, restart the NOMAD backend before testing again.")


if __name__ == "__main__":
    main()
