from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve the repository/server locations from this module instead of relying on
# the process working directory. The Windows dev launcher changes into `server`
# before starting Uvicorn, while some desktop/test launchers start from the repo
# root. Supporting both locations makes provider credentials deterministic.
_SERVER_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _SERVER_ROOT.parent


class Settings(BaseSettings):
    app_env: str = "development"
    app_secret_key: str = "change-me"
    public_base_url: str = "http://127.0.0.1:8765"
    database_url: str = "sqlite:///./data/nomad.db"
    data_dir: str = "data"
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_api_key: str = ""
    groq_api_key: str = ""
    groq_model: str = ""
    lastfm_api_key: str = ""
    genius_api_key: str = ""
    acoustid_api_key: str = ""

    # The repository-level .env is the normal Windows development location.
    # Keep server/.env supported for older setups and packaged/test layouts.
    # Real environment variables always take precedence over these files.
    model_config = SettingsConfigDict(
        env_file=(
            _REPO_ROOT / ".env",
            _SERVER_ROOT / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
