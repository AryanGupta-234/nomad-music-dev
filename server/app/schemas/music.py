from pydantic import BaseModel, Field, ConfigDict
from typing import Any

class TrackSourceOut(BaseModel):
    provider: str
    provider_id: str
    uri: str | None = None
    playback_kind: str | None = None
    available: bool = True

class TrackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    duration_ms: int | None = None
    artwork_url: str | None = None
    artist_id: str | None = None
    artist_name: str | None = None
    album_id: str | None = None
    album_name: str | None = None
    isrc: str | None = None
    sources: list[TrackSourceOut] = Field(default_factory=list)

class PlaylistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=500)
    description: str | None = None

class PlaylistOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    artwork_url: str | None = None
    tracks: list[TrackOut] = Field(default_factory=list)

class EventIn(BaseModel):
    track_id: str
    seconds: int = 0
    event_type: str = "play"
    profile_id: str | None = None

class SearchResult(BaseModel):
    track: TrackOut
    score: float = 0.0
    source: str = "local"

class VibeQuery(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    duration_minutes: int | None = None
    familiarity: float = 0.5
    energy: float | None = None
