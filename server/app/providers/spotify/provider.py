from __future__ import annotations

import base64
import time
from typing import Any

import httpx

from app.providers.base.provider import ProviderTrack


class SpotifyProvider:
    name = "spotify"
    api_base = "https://api.spotify.com/v1"
    token_url = "https://accounts.spotify.com/api/token"

    def __init__(self, client_id: str = "", client_secret: str = ""):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self._token: str | None = None
        self._token_expires_at = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    async def _access_token(self) -> str:
        if not self.configured:
            raise RuntimeError("Spotify client credentials are not configured")
        if self._token and time.time() < self._token_expires_at - 30:
            return self._token

        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                self.token_url,
                headers={"Authorization": f"Basic {basic}"},
                data={"grant_type": "client_credentials"},
            )
            response.raise_for_status()
            data = response.json()

        self._token = data["access_token"]
        self._token_expires_at = time.time() + int(data.get("expires_in", 3600))
        return self._token

    async def _request(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        token = await self._access_token()
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{self.api_base}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _map(item: dict[str, Any]) -> ProviderTrack:
        artists = item.get("artists") or []
        albums = item.get("album") or {}
        images = albums.get("images") or []
        external = item.get("external_urls") or {}
        return ProviderTrack(
            provider="spotify",
            provider_id=str(item.get("id")),
            title=item.get("name") or "Unknown",
            artist=(artists[0].get("name") if artists else "") or "",
            album=albums.get("name") or "",
            duration_ms=item.get("duration_ms"),
            artwork_url=(images[0].get("url") if images else None),
            uri=item.get("uri") or external.get("spotify"),
            metadata={
                "isrc": (item.get("external_ids") or {}).get("isrc"),
                "playback_kind": "spotify_sdk",
            },
        )

    async def search(self, query: str, limit: int = 10) -> list[ProviderTrack]:
        data = await self._request("/search", {"q": query, "type": "track", "limit": max(1, min(limit, 10))})
        return [self._map(item) for item in (data.get("tracks") or {}).get("items", [])]

    async def get_track(self, provider_id: str) -> ProviderTrack | None:
        if not provider_id:
            return None
        try:
            data = await self._request(f"/tracks/{provider_id}")
        except httpx.HTTPStatusError:
            return None
        return self._map(data)
