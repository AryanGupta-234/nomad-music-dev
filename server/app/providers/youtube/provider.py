from __future__ import annotations

from typing import Any

import httpx

from app.providers.base.provider import ProviderTrack


class YouTubeProvider:
    name = "youtube"
    base = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key.strip()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def search(self, query: str, limit: int = 10) -> list[ProviderTrack]:
        if not self.configured:
            return []
        safe_limit = max(1, min(limit, 50))
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoCategoryId": "10",
            "maxResults": safe_limit,
            "key": self.api_key,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.base}/search", params=params)
            response.raise_for_status()
            data = response.json()

        out: list[ProviderTrack] = []
        for item in data.get("items", []):
            video_id = ((item.get("id") or {}).get("videoId"))
            snippet = item.get("snippet") or {}
            if not video_id:
                continue
            out.append(
                ProviderTrack(
                    provider="youtube",
                    provider_id=video_id,
                    title=snippet.get("title") or "Unknown",
                    artist=snippet.get("channelTitle") or "",
                    album="",
                    duration_ms=None,
                    artwork_url=((snippet.get("thumbnails") or {}).get("high") or {}).get("url"),
                    uri=f"https://www.youtube.com/watch?v={video_id}",
                    metadata={"playback_kind": "youtube_external", "channel_id": snippet.get("channelId")},
                )
            )
        return out

    async def get_track(self, provider_id: str) -> ProviderTrack | None:
        if not self.configured or not provider_id:
            return None
        params: dict[str, Any] = {"part": "snippet,contentDetails", "id": provider_id, "key": self.api_key}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.base}/videos", params=params)
            if response.status_code != 200:
                return None
            data = response.json()
        item = next(iter(data.get("items") or []), None)
        if not item:
            return None
        snippet = item.get("snippet") or {}
        return ProviderTrack(
            provider="youtube",
            provider_id=provider_id,
            title=snippet.get("title") or "Unknown",
            artist=snippet.get("channelTitle") or "",
            artwork_url=((snippet.get("thumbnails") or {}).get("high") or {}).get("url"),
            uri=f"https://www.youtube.com/watch?v={provider_id}",
            metadata={"playback_kind": "youtube_external", "channel_id": snippet.get("channelId")},
        )
