from __future__ import annotations
import base64, hashlib, json, secrets
from datetime import datetime, timezone, timedelta
from urllib.parse import urlencode
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.config.settings import get_settings
from app.db.models import IntegrationAccount, OAuthState

def now(): return datetime.now(timezone.utc)
def _pkce_pair():
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge

def authorize_url(db: Session, provider: str, profile_id: str) -> str:
    st = secrets.token_urlsafe(32); verifier = challenge = None; cfg = get_settings()
    if provider == "spotify":
        if not cfg.spotify_client_id: raise ValueError("Spotify client ID is not configured")
        verifier, challenge = _pkce_pair()
    db.add(OAuthState(state=st, provider=provider, profile_id=profile_id, code_verifier=verifier)); db.commit()
    if provider == "spotify":
        p={"response_type":"code","client_id":cfg.spotify_client_id,"redirect_uri":f"{cfg.public_base_url}/api/v1/integrations/spotify/callback","scope":"user-read-private user-library-read playlist-read-private user-read-recently-played user-top-read streaming user-read-playback-state user-modify-playback-state","state":st,"code_challenge_method":"S256","code_challenge":challenge}
        return "https://accounts.spotify.com/authorize?"+urlencode(p)
    if provider == "youtube":
        if not (cfg.youtube_client_id and cfg.youtube_client_secret): raise ValueError("YouTube OAuth credentials are not configured")
        p={"client_id":cfg.youtube_client_id,"redirect_uri":f"{cfg.public_base_url}/api/v1/integrations/youtube/callback","response_type":"code","scope":"https://www.googleapis.com/auth/youtube.readonly","access_type":"offline","prompt":"consent","state":st}
        return "https://accounts.google.com/o/oauth2/v2/auth?"+urlencode(p)
    raise ValueError("unsupported provider")

async def callback(db: Session, provider: str, code: str, state: str):
    row=db.scalar(select(OAuthState).where(OAuthState.state==state,OAuthState.provider==provider))
    if not row: raise ValueError("invalid or expired OAuth state")
    cfg=get_settings(); profile_id=row.profile_id
    if provider=="spotify":
        payload={"grant_type":"authorization_code","code":code,"redirect_uri":f"{cfg.public_base_url}/api/v1/integrations/spotify/callback","client_id":cfg.spotify_client_id,"code_verifier":row.code_verifier or ""}; headers={}
        if cfg.spotify_client_secret and not row.code_verifier:
            basic=base64.b64encode(f"{cfg.spotify_client_id}:{cfg.spotify_client_secret}".encode()).decode(); headers={"Authorization":f"Basic {basic}"}; payload.pop("client_id",None)
        async with httpx.AsyncClient(timeout=15) as c:
            r=await c.post("https://accounts.spotify.com/api/token",headers=headers,data=payload); r.raise_for_status(); tok=r.json(); me=(await c.get("https://api.spotify.com/v1/me",headers={"Authorization":f"Bearer {tok['access_token']}"})).json()
    elif provider=="youtube":
        async with httpx.AsyncClient(timeout=15) as c:
            r=await c.post("https://oauth2.googleapis.com/token",data={"client_id":cfg.youtube_client_id,"client_secret":cfg.youtube_client_secret,"code":code,"grant_type":"authorization_code","redirect_uri":f"{cfg.public_base_url}/api/v1/integrations/youtube/callback"}); r.raise_for_status(); tok=r.json()
            me_resp=await c.get("https://www.googleapis.com/youtube/v3/channels",params={"part":"snippet","mine":"true"},headers={"Authorization":f"Bearer {tok['access_token']}"}); ch=next(iter((me_resp.json() if me_resp.is_success else {}).get("items") or []),None); me={"id":ch.get("id"),"title":(ch.get("snippet") or {}).get("title")} if ch else {}
    else: raise ValueError("unsupported provider")
    acc=db.scalar(select(IntegrationAccount).where(IntegrationAccount.profile_id==profile_id,IntegrationAccount.provider==provider))
    if not acc: acc=IntegrationAccount(profile_id=profile_id,provider=provider,access_token=""); db.add(acc)
    acc.access_token=tok.get("access_token",""); acc.refresh_token=tok.get("refresh_token") or acc.refresh_token; acc.expires_at=now()+timedelta(seconds=int(tok.get("expires_in",3600))); acc.scope=tok.get("scope"); acc.provider_user_id=me.get("id") or me.get("email"); acc.metadata_json=json.dumps(me); db.delete(row); db.commit(); db.refresh(acc); return acc

def statuses(db: Session):
    """Return normalized provider status objects for the default/local account view.

    The UI historically expected `name`, while OAuth records expose `provider`.
    Returning both fields keeps the connection contract stable and prevents a
    configured provider from being rendered as `Unavailable` merely because no
    OAuth account exists yet.
    """
    cfg=get_settings(); accounts={a.provider:a for a in db.scalars(select(IntegrationAccount)).all()}; out=[]
    for provider, configured, mode in [("spotify",bool(cfg.spotify_client_id),"pkce"),("youtube",bool(cfg.youtube_client_id and cfg.youtube_client_secret),"oauth")]:
        acc=accounts.get(provider)
        metadata={}
        if acc and acc.metadata_json:
            try: metadata=json.loads(acc.metadata_json or "{}")
            except Exception: metadata={}
        account_name=metadata.get("display_name") or metadata.get("title") or metadata.get("email") or metadata.get("id")
        out.append({"name":provider,"provider":provider,"configured":configured,"connected":bool(acc and acc.access_token),"authenticated":bool(acc and acc.access_token),"mode":mode,"account_name":account_name,"provider_user_id":acc.provider_user_id if acc else None,"expires_at":acc.expires_at.isoformat() if acc and acc.expires_at else None})
    return out

async def _refresh_if_needed(db: Session, acc: IntegrationAccount) -> None:
    if not acc.refresh_token or not acc.expires_at or acc.expires_at > now()+timedelta(seconds=60): return
    cfg=get_settings()
    async with httpx.AsyncClient(timeout=15) as c:
        if acc.provider=="spotify":
            payload={"grant_type":"refresh_token","refresh_token":acc.refresh_token,"client_id":cfg.spotify_client_id}; headers={}
            if cfg.spotify_client_secret:
                basic=base64.b64encode(f"{cfg.spotify_client_id}:{cfg.spotify_client_secret}".encode()).decode(); headers={"Authorization":f"Basic {basic}"}; payload.pop("client_id",None)
            r=await c.post("https://accounts.spotify.com/api/token",headers=headers,data=payload)
        elif acc.provider=="youtube":
            r=await c.post("https://oauth2.googleapis.com/token",data={"client_id":cfg.youtube_client_id,"client_secret":cfg.youtube_client_secret,"refresh_token":acc.refresh_token,"grant_type":"refresh_token"})
        else: return
        if r.is_success:
            tok=r.json(); acc.access_token=tok.get("access_token",acc.access_token); acc.refresh_token=tok.get("refresh_token") or acc.refresh_token; acc.expires_at=now()+timedelta(seconds=int(tok.get("expires_in",3600))); db.commit()

async def _oauth_get(db: Session, provider: str, profile_id: str, url: str, params=None) -> dict:
    acc=db.scalar(select(IntegrationAccount).where(IntegrationAccount.profile_id==profile_id,IntegrationAccount.provider==provider))
    if not acc: raise ValueError(f"{provider} is not connected for this profile")
    await _refresh_if_needed(db,acc)
    async with httpx.AsyncClient(timeout=20) as c:
        r=await c.get(url,params=params,headers={"Authorization":f"Bearer {acc.access_token}"})
        if r.status_code==401 and acc.refresh_token:
            acc.expires_at=now()-timedelta(seconds=1); await _refresh_if_needed(db,acc)
            r=await c.get(url,params=params,headers={"Authorization":f"Bearer {acc.access_token}"})
        r.raise_for_status(); return r.json()

async def spotify_library(db: Session, profile_id: str, page_limit: int = 50) -> dict:
    from app.core.tracks.service import upsert_provider_track
    from app.db.models import Playlist, ExternalCollection, PlayEvent
    from app.providers.spotify.provider import SpotifyProvider
    imported=collections=items=recent=0
    liked=db.scalar(select(ExternalCollection).where(ExternalCollection.profile_id==profile_id,ExternalCollection.provider=="spotify",ExternalCollection.provider_id=="__liked__"))
    if not liked:
        pl=Playlist(name="Spotify · Liked Songs",description="Imported from your Spotify library"); db.add(pl); db.flush(); liked=ExternalCollection(profile_id=profile_id,provider="spotify",provider_id="__liked__",local_playlist_id=pl.id,kind="liked"); db.add(liked); db.commit()
    offset=0; desired=[]
    while True:
        data=await _oauth_get(db,"spotify",profile_id,"https://api.spotify.com/v1/me/tracks",{"limit":page_limit,"offset":offset}); rows=data.get("items") or []
        for row in rows:
            item=row.get("track") or {}
            if item.get("type")!="track" or not item.get("id"): continue
            t=upsert_provider_track(db,SpotifyProvider._map(item)); desired.append(t.id); imported+=1
        if len(rows)<page_limit: break
        offset+=page_limit
    _reconcile_playlist(db,liked.local_playlist_id,desired); items+=len(desired)
    recent_data=await _oauth_get(db,"spotify",profile_id,"https://api.spotify.com/v1/me/player/recently-played",{"limit":50})
    for row in recent_data.get("items") or []:
        item=row.get("track") or {}
        if item.get("id"):
            t=upsert_provider_track(db,SpotifyProvider._map(item)); db.add(PlayEvent(track_id=t.id,profile_id=profile_id,event_type="play",seconds=0)); recent+=1
    offset=0
    while True:
        data=await _oauth_get(db,"spotify",profile_id,"https://api.spotify.com/v1/me/playlists",{"limit":page_limit,"offset":offset}); pls=data.get("items") or []
        for ext in pls:
            ext_id=ext.get("id")
            if not ext_id: continue
            mapping=db.scalar(select(ExternalCollection).where(ExternalCollection.profile_id==profile_id,ExternalCollection.provider=="spotify",ExternalCollection.provider_id==ext_id))
            if not mapping:
                pl=Playlist(name=f"Spotify · {ext.get('name') or 'Playlist'}",description=ext.get("description") or None,artwork_url=((ext.get("images") or [{}])[0]).get("url")); db.add(pl); db.flush(); mapping=ExternalCollection(profile_id=profile_id,provider="spotify",provider_id=ext_id,local_playlist_id=pl.id,kind="playlist"); db.add(mapping); db.commit(); collections+=1
            page=await _oauth_get(db,"spotify",profile_id,f"https://api.spotify.com/v1/playlists/{ext_id}/items",{"limit":page_limit,"offset":0}); wanted=[]
            for row in page.get("items") or []:
                item=row.get("item") or row.get("track") or {}
                if item.get("type")!="track" or not item.get("id"): continue
                wanted.append(upsert_provider_track(db,SpotifyProvider._map(item)).id)
            _reconcile_playlist(db,mapping.local_playlist_id,wanted); mapping.last_synced_at=now(); db.commit(); items+=len(wanted)
        if len(pls)<page_limit: break
        offset+=page_limit
    db.commit(); return {"provider":"spotify","imported_tracks":imported,"collections_created":collections,"playlist_items_synced":items,"recent_play_events_imported":recent}

async def youtube_library(db: Session, profile_id: str, page_limit: int = 50) -> dict:
    """Import YouTube likes/playlists. YouTube Data API does not expose private watch history."""
    from app.core.tracks.service import upsert_provider_track
    from app.db.models import ExternalCollection, Playlist
    from app.providers.base.provider import ProviderTrack
    imported=collections=items=0; me=await _oauth_get(db,"youtube",profile_id,"https://www.googleapis.com/youtube/v3/channels",{"part":"contentDetails,snippet","mine":"true"}); channel=next(iter(me.get("items") or []),None)
    if not channel: return {"provider":"youtube","imported_tracks":0,"collections_created":0,"playlist_items_synced":0,"history_supported":False}
    special=((channel.get("contentDetails") or {}).get("relatedPlaylists") or {}); specs=[]
    if special.get("likes"): specs.append(("__liked__",special["likes"],"liked","YouTube · Liked Videos"))
    data=await _oauth_get(db,"youtube",profile_id,"https://www.googleapis.com/youtube/v3/playlists",{"part":"snippet,contentDetails","mine":"true","maxResults":page_limit})
    for pl in data.get("items") or []: specs.append((pl.get("id"),pl.get("id"),"playlist",f"YouTube · {(pl.get('snippet') or {}).get('title') or 'Playlist'}"))
    for ext_id,actual_id,kind,name in specs:
        if not actual_id: continue
        mapping=db.scalar(select(ExternalCollection).where(ExternalCollection.profile_id==profile_id,ExternalCollection.provider=="youtube",ExternalCollection.provider_id==ext_id))
        if not mapping:
            pl=Playlist(name=name,description="Imported from YouTube"); db.add(pl); db.flush(); mapping=ExternalCollection(profile_id=profile_id,provider="youtube",provider_id=ext_id,local_playlist_id=pl.id,kind=kind); db.add(mapping); db.commit(); collections+=1
        token=None; wanted=[]
        while True:
            params={"part":"snippet,contentDetails","playlistId":actual_id,"maxResults":page_limit};
            if token: params["pageToken"]=token
            page=await _oauth_get(db,"youtube",profile_id,"https://www.googleapis.com/youtube/v3/playlistItems",params)
            for row in page.get("items") or []:
                sn=row.get("snippet") or {}; cd=row.get("contentDetails") or {}; vid=cd.get("videoId") or ((sn.get("resourceId") or {}).get("videoId"))
                if not vid: continue
                thumbs=sn.get("thumbnails") or {}; art=((thumbs.get("maxres") or {}).get("url") or f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg")
                t=upsert_provider_track(db,ProviderTrack(provider="youtube",provider_id=vid,title=sn.get("title") or "Unknown",artist=sn.get("videoOwnerChannelTitle") or sn.get("channelTitle") or "",artwork_url=art,uri=f"https://www.youtube.com/watch?v={vid}",metadata={"playback_kind":"youtube_external","channel_id":sn.get("channelId")})); wanted.append(t.id); imported+=1
            token=page.get("nextPageToken")
            if not token: break
        _reconcile_playlist(db,mapping.local_playlist_id,wanted); mapping.last_synced_at=now(); db.commit(); items+=len(wanted)
    return {"provider":"youtube","imported_tracks":imported,"collections_created":collections,"playlist_items_synced":items,"history_supported":False,"history_note":"YouTube Data API does not expose private watch history"}

def _reconcile_playlist(db: Session, playlist_id: str, desired_track_ids: list[str]) -> None:
    from app.db.models import PlaylistItem
    rows=db.scalars(select(PlaylistItem).where(PlaylistItem.playlist_id==playlist_id).order_by(PlaylistItem.position)).all(); by_track={r.track_id:r for r in rows}; seen=set(); desired=[]
    for tid in desired_track_ids:
        if tid not in seen: seen.add(tid); desired.append(tid)
    for r in rows:
        if r.track_id not in set(desired): db.delete(r)
    db.flush()
    for pos,tid in enumerate(desired):
        r=by_track.get(tid)
        if r: r.position=pos
        else: db.add(PlaylistItem(playlist_id=playlist_id,track_id=tid,position=pos))
    db.commit()

async def sync_all_libraries(db: Session, profile_id: str) -> dict:
    """Best-effort provider synchronization: one provider failure never blocks the other."""
    result={"profile_id":profile_id,"spotify":None,"youtube":None,"errors":{}}
    for provider,fn in (("spotify",spotify_library),("youtube",youtube_library)):
        try: result[provider]=await fn(db,profile_id)
        except Exception as exc: result["errors"][provider]=f"{type(exc).__name__}: {exc}"
    result["ok"]=not result["errors"]; return result
