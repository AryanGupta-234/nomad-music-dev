from __future__ import annotations
import base64, hashlib, json, secrets, time
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config.settings import get_settings
from app.db.models import IntegrationAccount, OAuthState

def now(): return datetime.now(timezone.utc)
def _pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge

def authorize_url(db: Session, provider: str, profile_id: str) -> str:
    st = secrets.token_urlsafe(32)
    verifier = None
    challenge = None
    cfg = get_settings()
    if provider == "spotify":
        if not cfg.spotify_client_id:
            raise ValueError("Spotify client ID is not configured")
        verifier, challenge = _pkce_pair()
    db.add(OAuthState(state=st, provider=provider, profile_id=profile_id, code_verifier=verifier))
    db.commit()
    if provider == "spotify":
        p = {
            "response_type": "code",
            "client_id": cfg.spotify_client_id,
            "redirect_uri": f"{cfg.public_base_url}/api/v1/integrations/spotify/callback",
            "scope": "user-read-private user-library-read playlist-read-private user-read-recently-played user-top-read streaming user-read-playback-state user-modify-playback-state",
            "state": st,
            "code_challenge_method": "S256",
            "code_challenge": challenge,
        }
        return "https://accounts.spotify.com/authorize?" + urlencode(p)
    if provider == "youtube":
        if not (cfg.youtube_client_id and cfg.youtube_client_secret):
            raise ValueError("YouTube OAuth credentials are not configured")
        p = {
            "client_id": cfg.youtube_client_id,
            "redirect_uri": f"{cfg.public_base_url}/api/v1/integrations/youtube/callback",
            "response_type": "code",
            "scope": "https://www.googleapis.com/auth/youtube.readonly",
            "access_type": "offline",
            "prompt": "consent",
            "state": st,
        }
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(p)
    raise ValueError("unsupported provider")

async def callback(db: Session, provider: str, code: str, state: str):
    row=db.scalar(select(OAuthState).where(OAuthState.state==state,OAuthState.provider==provider))
    if not row: raise ValueError('invalid or expired OAuth state')
    cfg=get_settings(); profile_id=row.profile_id
    if provider=='spotify':
        payload={
            'grant_type':'authorization_code',
            'code':code,
            'redirect_uri':f'{cfg.public_base_url}/api/v1/integrations/spotify/callback',
            'client_id':cfg.spotify_client_id,
            'code_verifier':row.code_verifier or '',
        }
        headers={}
        if cfg.spotify_client_secret and not row.code_verifier:
            basic=base64.b64encode(f'{cfg.spotify_client_id}:{cfg.spotify_client_secret}'.encode()).decode()
            headers={'Authorization':f'Basic {basic}'}
            payload.pop('client_id',None)
        async with httpx.AsyncClient(timeout=15) as c:
            r=await c.post('https://accounts.spotify.com/api/token',headers=headers,data=payload); r.raise_for_status(); tok=r.json(); me=(await c.get('https://api.spotify.com/v1/me',headers={'Authorization':f"Bearer {tok['access_token']}"})).json()
    elif provider=='youtube':
        async with httpx.AsyncClient(timeout=15) as c:
            r=await c.post('https://oauth2.googleapis.com/token',data={'client_id':cfg.youtube_client_id,'client_secret':cfg.youtube_client_secret,'code':code,'grant_type':'authorization_code','redirect_uri':f'{cfg.public_base_url}/api/v1/integrations/youtube/callback'}); r.raise_for_status(); tok=r.json()
            me_resp = await c.get('https://www.googleapis.com/youtube/v3/channels', params={'part':'snippet','mine':'true'}, headers={'Authorization':f"Bearer {tok['access_token']}"})
            me_data = me_resp.json() if me_resp.is_success else {}
            ch = next(iter(me_data.get('items') or []), None)
            me = {'id': ch.get('id')} if ch else {}
    else: raise ValueError('unsupported provider')
    acc=db.scalar(select(IntegrationAccount).where(IntegrationAccount.profile_id==profile_id,IntegrationAccount.provider==provider))
    if not acc: acc=IntegrationAccount(profile_id=profile_id,provider=provider,access_token=''); db.add(acc)
    acc.access_token=tok.get('access_token',''); acc.refresh_token=tok.get('refresh_token') or acc.refresh_token; acc.expires_at=now()+timedelta(seconds=int(tok.get('expires_in',3600))); acc.scope=tok.get('scope'); acc.provider_user_id=me.get('id') or me.get('email'); acc.metadata_json=json.dumps(me); db.delete(row); db.commit(); db.refresh(acc); return acc
def statuses(db: Session):
    cfg = get_settings()
    accounts = {a.provider: a for a in db.scalars(select(IntegrationAccount)).all()}
    out = []
    for provider, configured, mode in [
        ("spotify", bool(cfg.spotify_client_id), "pkce"),
        ("youtube", bool(cfg.youtube_client_id and cfg.youtube_client_secret), "oauth"),
    ]:
        acc = accounts.get(provider)
        out.append({
            "provider": provider,
            "configured": configured,
            "connected": bool(acc and acc.access_token),
            "mode": mode,
            "provider_user_id": acc.provider_user_id if acc else None,
            "expires_at": acc.expires_at.isoformat() if acc and acc.expires_at else None,
        })
    return out


async def spotify_library_mutation(db: Session, profile_id: str, uris: list[str], remove: bool = False) -> dict:
    if not uris:
        return {"ok": True, "count": 0, "removed": remove}
    endpoint = "https://api.spotify.com/v1/me/library"
    method = "DELETE" if remove else "PUT"
    acc = db.scalar(select(IntegrationAccount).where(IntegrationAccount.profile_id == profile_id, IntegrationAccount.provider == "spotify"))
    if not acc:
        raise ValueError("spotify is not connected for this profile")
    cfg = get_settings()
    chunks = [uris[i:i+40] for i in range(0, len(uris), 40)]

    async def refresh(c):
        if not acc.refresh_token:
            return False
        payload = {"grant_type": "refresh_token", "refresh_token": acc.refresh_token, "client_id": cfg.spotify_client_id}
        headers = {}
        if cfg.spotify_client_secret:
            basic = base64.b64encode(f"{cfg.spotify_client_id}:{cfg.spotify_client_secret}".encode()).decode()
            headers = {"Authorization": f"Basic {basic}"}
            payload.pop("client_id", None)
        rr = await c.post("https://accounts.spotify.com/api/token", headers=headers, data=payload)
        if not rr.is_success:
            return False
        tok = rr.json()
        acc.access_token = tok.get("access_token", acc.access_token)
        if tok.get("refresh_token"):
            acc.refresh_token = tok["refresh_token"]
        acc.expires_at = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
        db.commit()
        return True

    async with httpx.AsyncClient(timeout=15) as c:
        headers = {"Authorization": f"Bearer {acc.access_token}"}
        for chunk in chunks:
            params = [("uris", uri) for uri in chunk]
            r = await c.request(method, endpoint, headers=headers, params=params)
            if r.status_code == 401 and await refresh(c):
                headers = {"Authorization": f"Bearer {acc.access_token}"}
                r = await c.request(method, endpoint, headers=headers, params=params)
            r.raise_for_status()
    return {"ok": True, "count": len(uris), "removed": remove}

async def spotify_library_contains(db: Session, profile_id: str, uris: list[str]) -> dict:
    if not uris:
        return {"ok": True, "items": []}
    acc = db.scalar(select(IntegrationAccount).where(IntegrationAccount.profile_id == profile_id, IntegrationAccount.provider == "spotify"))
    if not acc:
        raise ValueError("spotify is not connected for this profile")
    cfg = get_settings()
    chunks = [uris[i:i+40] for i in range(0, len(uris), 40)]
    results = []
    async with httpx.AsyncClient(timeout=15) as c:
        headers = {"Authorization": f"Bearer {acc.access_token}"}
        for chunk in chunks:
            r = await c.get("https://api.spotify.com/v1/me/library/contains", headers=headers, params=[("uris", uri) for uri in chunk])
            if r.status_code == 401 and acc.refresh_token:
                payload = {"grant_type": "refresh_token", "refresh_token": acc.refresh_token, "client_id": cfg.spotify_client_id}
                refresh_headers = {}
                if cfg.spotify_client_secret:
                    basic = base64.b64encode(f"{cfg.spotify_client_id}:{cfg.spotify_client_secret}".encode()).decode()
                    refresh_headers = {"Authorization": f"Basic {basic}"}
                    payload.pop("client_id", None)
                rr = await c.post("https://accounts.spotify.com/api/token", headers=refresh_headers, data=payload)
                rr.raise_for_status()
                tok = rr.json(); acc.access_token = tok.get("access_token", acc.access_token)
                if tok.get("refresh_token"): acc.refresh_token = tok["refresh_token"]
                acc.expires_at = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
                db.commit(); headers = {"Authorization": f"Bearer {acc.access_token}"}
                r = await c.get("https://api.spotify.com/v1/me/library/contains", headers=headers, params=[("uris", uri) for uri in chunk])
            r.raise_for_status()
            results.extend(r.json() or [])
    return {"ok": True, "items": results}

async def _oauth_get(db: Session, provider: str, profile_id: str, url: str, params: dict | None = None) -> dict:
    """Authenticated GET using the stored user integration token."""
    acc = db.scalar(select(IntegrationAccount).where(
        IntegrationAccount.profile_id == profile_id,
        IntegrationAccount.provider == provider,
    ))
    if not acc:
        raise ValueError(f"{provider} is not connected for this profile")
    cfg = get_settings()
    token = acc.access_token

    async with httpx.AsyncClient(timeout=20) as c:
        r = await c.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 401 and acc.refresh_token:
            if provider == "spotify":
                payload = {"grant_type": "refresh_token", "refresh_token": acc.refresh_token, "client_id": cfg.spotify_client_id}
                headers = {}
                if cfg.spotify_client_secret:
                    basic = base64.b64encode(f"{cfg.spotify_client_id}:{cfg.spotify_client_secret}".encode()).decode()
                    headers = {"Authorization": f"Basic {basic}"}
                    payload.pop("client_id", None)
                rr = await c.post("https://accounts.spotify.com/api/token", headers=headers, data=payload)
            elif provider == "youtube":
                rr = await c.post("https://oauth2.googleapis.com/token", data={
                    "client_id": cfg.youtube_client_id,
                    "client_secret": cfg.youtube_client_secret,
                    "refresh_token": acc.refresh_token,
                    "grant_type": "refresh_token",
                })
            else:
                rr = None
            if rr is not None and rr.is_success:
                tok = rr.json()
                acc.access_token = tok.get("access_token", acc.access_token)
                if tok.get("refresh_token"):
                    acc.refresh_token = tok["refresh_token"]
                acc.expires_at = now() + timedelta(seconds=int(tok.get("expires_in", 3600)))
                db.commit()
                r = await c.get(url, params=params, headers={"Authorization": f"Bearer {acc.access_token}"})
        r.raise_for_status()
        return r.json()


async def spotify_library(db: Session, profile_id: str, page_limit: int = 50) -> dict:
    """Pull the authenticated user's saved tracks and playlists into the NOMAD graph.

    This intentionally imports metadata/playlist membership only; Spotify audio is never downloaded.
    """
    from app.core.tracks.service import upsert_provider_track
    from app.db.models import TrackSource, Playlist, PlaylistItem, ExternalCollection
    from sqlalchemy import select, delete
    from datetime import datetime, timezone

    imported = 0
    collections = 0
    items = 0
    liked = db.scalar(select(ExternalCollection).where(
        ExternalCollection.profile_id == profile_id,
        ExternalCollection.provider == "spotify",
        ExternalCollection.provider_id == "__liked__",
    ))
    if not liked:
        pl = Playlist(name="Spotify · Liked Songs", description="Imported from your Spotify library")
        db.add(pl); db.flush()
        liked = ExternalCollection(profile_id=profile_id, provider="spotify", provider_id="__liked__", local_playlist_id=pl.id, kind="liked")
        db.add(liked); db.commit()
    liked_playlist = db.get(Playlist, liked.local_playlist_id)

    offset = 0
    while True:
        data = await _oauth_get(db, "spotify", profile_id, "https://api.spotify.com/v1/me/tracks", {"limit": page_limit, "offset": offset})
        rows = data.get("items") or []
        if not rows:
            break
        desired = []
        for row in rows:
            item = row.get("track") or {}
            if not item or item.get("type") != "track" or not item.get("id"):
                continue
            from app.providers.spotify.provider import SpotifyProvider
            t = upsert_provider_track(db, SpotifyProvider._map(item)); desired.append(t.id); imported += 1
        _reconcile_playlist(db, liked_playlist.id, desired)
        items += len(desired)
        if len(rows) < page_limit: break
        offset += page_limit
    liked.updated_at = datetime.now(timezone.utc)

    offset = 0
    while True:
        data = await _oauth_get(db, "spotify", profile_id, "https://api.spotify.com/v1/me/playlists", {"limit": page_limit, "offset": offset})
        pls = data.get("items") or []
        if not pls: break
        for ext in pls:
            ext_id = ext.get("id")
            if not ext_id: continue
            mapping = db.scalar(select(ExternalCollection).where(
                ExternalCollection.profile_id == profile_id,
                ExternalCollection.provider == "spotify",
                ExternalCollection.provider_id == ext_id,
            ))
            if not mapping:
                pl = Playlist(name=f"Spotify · {ext.get('name') or 'Playlist'}", description=ext.get('description') or None, artwork_url=((ext.get('images') or [{}])[0]).get('url'))
                db.add(pl); db.flush()
                mapping = ExternalCollection(profile_id=profile_id, provider="spotify", provider_id=ext_id, local_playlist_id=pl.id, kind="playlist")
                db.add(mapping); db.commit(); collections += 1
            data2 = await _oauth_get(db, "spotify", profile_id, f"https://api.spotify.com/v1/playlists/{ext_id}/items", {"limit": page_limit, "offset": 0})
            desired=[]
            for row in data2.get("items") or []:
                item=row.get("item") or row.get("track") or {}
                if item.get("type") != "track" or not item.get("id"): continue
                from app.providers.spotify.provider import SpotifyProvider
                t=upsert_provider_track(db, SpotifyProvider._map(item)); desired.append(t.id)
            _reconcile_playlist(db, mapping.local_playlist_id, desired)
            mapping.last_synced_at=datetime.now(timezone.utc); db.commit(); items += len(desired)
        if len(pls) < page_limit: break
        offset += page_limit

    db.commit()
    return {"provider": "spotify", "imported_tracks": imported, "collections_created": collections, "playlist_items_synced": items}


async def youtube_library(db: Session, profile_id: str, page_limit: int = 50) -> dict:
    """Import authenticated YouTube playlists and liked videos into the canonical graph."""
    from app.core.tracks.service import upsert_provider_track
    from app.providers.youtube.provider import YouTubeProvider
    from app.db.models import ExternalCollection, Playlist
    from sqlalchemy import select
    from datetime import datetime, timezone
    cfg=get_settings()
    if not cfg.youtube_client_id or not cfg.youtube_client_secret:
        raise ValueError("YouTube OAuth credentials are not configured")

    me = await _oauth_get(db, "youtube", profile_id, "https://www.googleapis.com/youtube/v3/channels", {"part":"contentDetails,snippet", "mine":"true"})
    channel = next(iter(me.get("items") or []), None)
    if not channel: return {"provider":"youtube","imported_tracks":0,"collections_created":0,"playlist_items_synced":0}
    special = ((channel.get("contentDetails") or {}).get("relatedPlaylists") or {})
    playlist_specs=[("__liked__", special.get("likes"), "liked", "YouTube · Liked Videos")]
    data = await _oauth_get(db, "youtube", profile_id, "https://www.googleapis.com/youtube/v3/playlists", {"part":"snippet,contentDetails", "mine":"true", "maxResults":page_limit})
    for pl in data.get("items") or []:
        playlist_specs.append((pl.get("id"), pl.get("id"), "playlist", f"YouTube · {(pl.get('snippet') or {}).get('title') or 'Playlist'}"))

    imported=collections=items=0
    for ext_id, actual_id, kind, name in playlist_specs:
        if not actual_id: continue
        mapping=db.scalar(select(ExternalCollection).where(
            ExternalCollection.profile_id==profile_id, ExternalCollection.provider=="youtube", ExternalCollection.provider_id==ext_id))
        if not mapping:
            pl=Playlist(name=name, description="Imported from YouTube")
            db.add(pl); db.flush(); mapping=ExternalCollection(profile_id=profile_id,provider="youtube",provider_id=ext_id,local_playlist_id=pl.id,kind=kind); db.add(mapping); db.commit(); collections+=1
        page_token=None; desired=[]
        while True:
            params={"part":"snippet,contentDetails", "playlistId":actual_id, "maxResults":page_limit}
            if page_token: params["pageToken"]=page_token
            page=await _oauth_get(db,"youtube",profile_id,"https://www.googleapis.com/youtube/v3/playlistItems",params)
            for row in page.get("items") or []:
                sn=row.get("snippet") or {}; cd=row.get("contentDetails") or {}
                vid=cd.get("videoId") or ((sn.get("resourceId") or {}).get("videoId"))
                if not vid: continue
                title=sn.get("title") or "Unknown"
                channel_title=sn.get("videoOwnerChannelTitle") or sn.get("channelTitle") or ""
                from app.providers.base.provider import ProviderTrack
                t=upsert_provider_track(db, ProviderTrack(provider="youtube",provider_id=vid,title=title,artist=channel_title,artwork_url=((sn.get("thumbnails") or {}).get("high") or {}).get("url"),uri=f"https://www.youtube.com/watch?v={vid}",metadata={"playback_kind":"youtube_external","channel_id":sn.get("channelId")}))
                desired.append(t.id); imported+=1
            page_token=page.get("nextPageToken")
            if not page_token: break
        from app.services.integrations import _reconcile_playlist
        _reconcile_playlist(db,mapping.local_playlist_id,desired)
        mapping.last_synced_at=datetime.now(timezone.utc); db.commit(); items+=len(desired)
    return {"provider":"youtube","imported_tracks":imported,"collections_created":collections,"playlist_items_synced":items}


def _reconcile_playlist(db: Session, playlist_id: str, desired_track_ids: list[str]) -> None:
    from app.db.models import PlaylistItem
    from sqlalchemy import select, delete
    rows=db.scalars(select(PlaylistItem).where(PlaylistItem.playlist_id==playlist_id).order_by(PlaylistItem.position)).all()
    by_track={r.track_id:r for r in rows}
    desired=[]; seen=set()
    for tid in desired_track_ids:
        if tid in seen: continue
        seen.add(tid); desired.append(tid)
    desired_set=set(desired)
    for r in rows:
        if r.track_id not in desired_set: db.delete(r)
    db.flush()
    for pos, tid in enumerate(desired):
        r=by_track.get(tid)
        if r is None:
            r=db.scalar(select(PlaylistItem).where(PlaylistItem.playlist_id==playlist_id, PlaylistItem.track_id==tid))
        if r: r.position=pos
        else: db.add(PlaylistItem(playlist_id=playlist_id,track_id=tid,position=pos))
    db.commit()
