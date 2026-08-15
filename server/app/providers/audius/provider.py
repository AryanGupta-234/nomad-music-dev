import httpx
from app.providers.base.provider import ProviderTrack


class AudiusProvider:
    """Audius is an open, decentralized music protocol: independent/CC-licensed
    artists, full-length tracks, genuinely free and streamable with no OAuth,
    no API key, and no per-account gating (unlike Spotify/YouTube). The
    catalog is not the mainstream commercial catalog, but every track that
    resolves here plays in full, immediately, for anyone.

    api.audius.co is a stable load-balanced gateway across Audius discovery
    nodes - no need to pick/rotate a node manually.
    """

    name = "audius"
    base = "https://api.audius.co/v1"
    app_name = "NOMAD"

    @staticmethod
    def _map(x: dict) -> ProviderTrack | None:
        track_id = x.get("id")
        if not track_id:
            return None
        artwork = x.get("artwork") or {}
        art = artwork.get("480x480") or artwork.get("150x150") or artwork.get("1000x1000")
        user = x.get("user") or {}
        stream_url = f"https://api.audius.co/v1/tracks/{track_id}/stream?app_name=NOMAD"
        return ProviderTrack(
            "audius", str(track_id), x.get("title") or "Unknown",
            user.get("name") or user.get("handle") or "",
            (x.get("album") or {}).get("title", "") if isinstance(x.get("album"), dict) else "",
            int((x.get("duration") or 0)) * 1000, art,
            stream_url,
            {"playback_kind": "audius_stream", "permalink": x.get("permalink")},
        )

    async def search(self, query: str, limit: int = 10) -> list[ProviderTrack]:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{self.base}/tracks/search", params={"query": query, "app_name": self.app_name, "limit": limit})
            r.raise_for_status()
            rows = r.json().get("data") or []
        out = [self._map(x) for x in rows]
        return [t for t in out if t]

    async def get_track(self, provider_id: str):
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{self.base}/tracks/{provider_id}", params={"app_name": self.app_name})
            if r.status_code != 200:
                return None
            row = r.json().get("data")
        return self._map(row) if row else None
