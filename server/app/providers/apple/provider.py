import httpx
from app.providers.base.provider import ProviderTrack

class AppleProvider:
    name = "apple"
    base = "https://itunes.apple.com/search"

    @staticmethod
    def _map(x: dict) -> ProviderTrack:
        # iTunes/Apple's public catalog API only ever offers a 30-second
        # preview clip (previewUrl), never a full track - there is no
        # licensing path to full playback here. trackViewUrl is just a
        # web page, not audio, so it's useless as a playback source and
        # was previously stored as the source `uri`, which meant nothing
        # ever actually played. Store the real preview audio URL instead
        # and tag it so the player knows this is a 30s clip, not a full track.
        preview = x.get("previewUrl")
        return ProviderTrack(
            "apple", str(x.get("trackId")), x.get("trackName") or "Unknown",
            x.get("artistName") or "", x.get("collectionName") or "",
            int((x.get("trackTimeMillis") or 0)), x.get("artworkUrl100"),
            preview,
            {"preview_url": preview, "release_date": x.get("releaseDate"),
             "playback_kind": "preview_30s" if preview else "unavailable",
             "web_url": x.get("trackViewUrl")},
        )

    async def search(self, query: str, limit: int = 10) -> list[ProviderTrack]:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(self.base, params={"term": query, "entity": "song", "limit": limit})
            r.raise_for_status()
            rows = r.json().get("results", [])
        return [self._map(x) for x in rows if x.get("trackId")]

    async def get_track(self, provider_id: str):
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get("https://itunes.apple.com/lookup", params={"id": provider_id})
            if r.status_code != 200:
                return None
            rows = r.json().get("results", [])
        return next(iter([self._map(x) for x in rows if x.get("trackId")]), None)
