from __future__ import annotations
import base64
from datetime import datetime, timezone, timedelta
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config.settings import get_settings
from app.db.models import IntegrationAccount
from app.providers.spotify.provider import SpotifyProvider

async def get_spotify_access_token(db: Session, profile_id: str) -> str:
    cfg = get_settings()
    acc = db.scalar(select(IntegrationAccount).where(
        IntegrationAccount.profile_id == profile_id,
        IntegrationAccount.provider == "spotify",
    ))
    if not acc or not acc.access_token:
        raise ValueError("Spotify is not connected")
    now = datetime.now(timezone.utc)
    expires = acc.expires_at
    if expires and expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if not expires or expires > now + timedelta(seconds=45):
        return acc.access_token
    if not acc.refresh_token:
        return acc.access_token
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": acc.refresh_token,
        "client_id": cfg.spotify_client_id,
    }
    headers = {}
    if cfg.spotify_client_secret:
        basic = base64.b64encode(f"{cfg.spotify_client_id}:{cfg.spotify_client_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {basic}"}
        payload.pop("client_id", None)
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(SpotifyProvider.token_url, headers=headers, data=payload)
        r.raise_for_status()
        tok = r.json()
    acc.access_token = tok.get("access_token", acc.access_token)
    if tok.get("refresh_token"):
        acc.refresh_token = tok["refresh_token"]
    acc.expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tok.get("expires_in", 3600)))
    db.commit()
    return acc.access_token

async def spotify_user_search(db: Session, profile_id: str, query: str, limit: int = 10):
    token = await get_spotify_access_token(db, profile_id)
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(
            f"{SpotifyProvider.api_base}/search",
            params={"q": query, "type": "track", "limit": max(1, min(limit, 10))},
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        data = r.json()
    return [SpotifyProvider._map(item) for item in (data.get("tracks") or {}).get("items", [])]
