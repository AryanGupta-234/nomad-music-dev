from app.providers.base.provider import ProviderTrack

class MockMusicProvider:
    name = "mock"

    async def search(self, query: str, limit: int = 10) -> list[ProviderTrack]:
        seeds = [
            ("Midnight Drive", "NOMAD Sample", 214000),
            ("Neon Rain", "NOMAD Sample", 198000),
            ("Afterglow", "NOMAD Sample", 231000),
            ("Night Signals", "NOMAD Sample", 205000),
        ]
        q = query.lower().strip()
        results = [
            ProviderTrack("mock", str(i), title, artist, duration_ms=dur)
            for i, (title, artist, dur) in enumerate(seeds, 1)
            if not q or q in title.lower() or q in artist.lower()
        ]
        return results[:limit]

    async def get_track(self, provider_id: str):
        rows = await self.search("", 10)
        return next((x for x in rows if x.provider_id == provider_id), None)
