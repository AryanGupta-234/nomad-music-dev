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

    @staticmethod
    def _best_thumbnail(thumbnails: dict[str, Any], video_id: str | None = None) -> str | None:
        """Prefer the highest-resolution YouTube thumbnail available."""
        if video_id:
            # maxresdefault is normally 1280px wide. The browser can fall back
            # to the API-provided image if an individual video has no maxres.
            return f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"

        maxres = thumbnails.get("maxres") or {}
        if maxres.get("url"):
            return maxres["url"]
        candidates = [value for value in thumbnails.values() if isinstance(value, dict) and value.get("url")]
        if not candidates:
            return None
        sized = [value for value in candidates if isinstance(value.get("width"), (int, float))]
        if sized:
            return max(sized, key=lambda value: float(value.get("width") or 0)).get("url")
        return candidates[0].get("url")

    @staticmethod
    def _map_item(item: dict[str, Any]) -> ProviderTrack | None:
        video_id = ((item.get("id") or {}).get("videoId")) or item.get("id")
        snippet = item.get("snippet") or {}
        if isinstance(video_id, dict) or not video_id:
            return None
        return ProviderTrack(
            provider="youtube",
            provider_id=str(video_id),
            title=snippet.get("title") or "Unknown",
            artist=snippet.get("channelTitle") or "",
            album="",
            duration_ms=None,
            artwork_url=YouTubeProvider._best_thumbnail(snippet.get("thumbnails") or {}, str(video_id)),
            uri=f"https://www.youtube.com/watch?v={video_id}",
            metadata={"playback_kind": "youtube_external", "channel_id": snippet.get("channelId")},
        )

    async def search(self, query: str, limit: int = 10) -> list[ProviderTrack]:
        if not self.configured:
            return []
        safe_limit = max(1, min(limit, 50))
        params = {"part": "snippet", "q": query, "type": "video", "videoCategoryId": "10", "maxResults": safe_limit, "key": self.api_key}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.base}/search", params=params)
            response.raise_for_status()
            data = response.json()
        out: list[ProviderTrack] = []
        for item in data.get("items", []):
            track = self._map_item(item)
            if track:
                out.append(track)
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
        return self._map_item(item)
