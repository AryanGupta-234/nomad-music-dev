import httpx
from app.providers.base.provider import ProviderTrack

class DeezerProvider:
    name = "deezer"
    base = "https://api.deezer.com"

    async def search(self, query: str, limit: int = 10) -> list[ProviderTrack]:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{self.base}/search", params={"q": query, "limit": limit})
            r.raise_for_status()
            rows = r.json().get("data", [])
        return [ProviderTrack(self.name, str(x["id"]), x.get("title") or "Unknown", (x.get("artist") or {}).get("name", ""), (x.get("album") or {}).get("title", ""), (x.get("duration") or 0) * 1000, (x.get("album") or {}).get("cover_medium"), x.get("link"), {"preview_url": x.get("preview")}) for x in rows]

    async def get_track(self, provider_id: str):
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{self.base}/track/{provider_id}")
            if r.status_code != 200:
                return None
            x = r.json()
        return ProviderTrack(self.name, str(x["id"]), x.get("title") or "Unknown", (x.get("artist") or {}).get("name", ""), (x.get("album") or {}).get("title", ""), (x.get("duration") or 0) * 1000, (x.get("album") or {}).get("cover_medium"), x.get("link"), {"preview_url": x.get("preview")})
