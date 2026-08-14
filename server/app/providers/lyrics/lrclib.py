import httpx

class LRCLIBProvider:
    name = "lrclib"
    base = "https://lrclib.net/api"

    async def search(self, title: str, artist: str, duration_ms: int | None = None):
        q = f"{artist} {title}".strip()
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(f"{self.base}/search", params={"q": q})
            r.raise_for_status()
            rows = r.json()
        def score(row):
            rt = (row.get("trackName") or "").lower(); ra = (row.get("artistName") or "").lower()
            target = title.lower(); art = artist.lower()
            s = (1 if target and target in rt else 0) + (1 if art and art in ra else 0)
            if duration_ms and row.get("duration"):
                if abs(int(row["duration"]*1000) - duration_ms) < 3000: s += 1
            return s
        rows = sorted(rows, key=score, reverse=True)
        if not rows: return None
        x = rows[0]
        return {"title": x.get("trackName") or title, "artist": x.get("artistName") or artist, "plain": x.get("plainLyrics") or "", "synced": x.get("syncedLyrics") or "", "source": self.name}
