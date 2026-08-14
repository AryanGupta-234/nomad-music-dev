import httpx
from app.providers.base.provider import ProviderTrack

class AppleProvider:
    name = "apple"
    base = "https://itunes.apple.com/search"

    async def search(self, query: str, limit: int = 10) -> list[ProviderTrack]:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(self.base, params={"term": query, "entity": "song", "limit": limit})
            r.raise_for_status()
            rows = r.json().get("results", [])
        return [ProviderTrack(self.name, str(x.get("trackId")), x.get("trackName") or "Unknown", x.get("artistName") or "", x.get("collectionName") or "", int((x.get("trackTimeMillis") or 0)), x.get("artworkUrl100"), x.get("trackViewUrl"), {"preview_url": x.get("previewUrl"), "release_date": x.get("releaseDate")}) for x in rows if x.get("trackId")]

    async def get_track(self, provider_id: str):
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get("https://itunes.apple.com/lookup", params={"id": provider_id})
            if r.status_code != 200:
                return None
            rows = r.json().get("results", [])
        return next(iter([ProviderTrack(self.name, str(x.get("trackId")), x.get("trackName") or "Unknown", x.get("artistName") or "", x.get("collectionName") or "", int((x.get("trackTimeMillis") or 0)), x.get("artworkUrl100"), x.get("trackViewUrl"), {"preview_url": x.get("previewUrl"), "release_date": x.get("releaseDate")}) for x in rows if x.get("trackId")]), None)
