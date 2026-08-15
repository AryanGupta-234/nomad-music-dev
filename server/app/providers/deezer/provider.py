import httpx
from app.providers.base.provider import ProviderTrack

class DeezerProvider:
    name = "deezer"
    base = "https://api.deezer.com"

    @staticmethod
    def _map(x: dict) -> ProviderTrack:
        # Same situation as Apple: Deezer's public (unauthenticated) API only
        # exposes a 30-second preview clip. `link` is a webpage, not audio -
        # storing that as the playback `uri` (as before) meant every Deezer
        # source silently could never actually play. Use the real preview
        # stream URL and mark the kind so playback code knows what it has.
        preview = x.get("preview")
        return ProviderTrack(
            "deezer", str(x["id"]), x.get("title") or "Unknown",
            (x.get("artist") or {}).get("name", ""), (x.get("album") or {}).get("title", ""),
            (x.get("duration") or 0) * 1000, (x.get("album") or {}).get("cover_medium"),
            preview,
            {"preview_url": preview,
             "playback_kind": "preview_30s" if preview else "unavailable",
             "web_url": x.get("link")},
        )

    async def search(self, query: str, limit: int = 10) -> list[ProviderTrack]:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{self.base}/search", params={"q": query, "limit": limit})
            r.raise_for_status()
            rows = r.json().get("data", [])
        return [self._map(x) for x in rows]

    async def get_track(self, provider_id: str):
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{self.base}/track/{provider_id}")
            if r.status_code != 200:
                return None
            x = r.json()
        return self._map(x)
