from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()
