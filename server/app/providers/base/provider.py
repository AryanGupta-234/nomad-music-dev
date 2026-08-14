from dataclasses import dataclass, field
from typing import Protocol

@dataclass
class ProviderTrack:
    provider: str
    provider_id: str
    title: str
    artist: str = ""
    album: str = ""
    duration_ms: int | None = None
    artwork_url: str | None = None
    uri: str | None = None
    metadata: dict = field(default_factory=dict)

class MusicProvider(Protocol):
    name: str
    async def search(self, query: str, limit: int = 10) -> list[ProviderTrack]: ...
    async def get_track(self, provider_id: str) -> ProviderTrack | None: ...

class LyricsProvider(Protocol):
    name: str
    async def search(self, title: str, artist: str, duration_ms: int | None = None) -> dict | None: ...
