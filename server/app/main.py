from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
import asyncio, json
from app.config.settings import get_settings
from app.db.session import get_db
from app.db.models import Track, TrackSource, Playlist, PlaylistItem, PlayEvent, Profile, UserSignal, BackgroundJob, Lyrics, RecommendationCandidate, AudioFeature
from app.schemas.music import TrackOut, TrackSourceOut, PlaylistCreate, PlaylistOut, EventIn, VibeQuery
from app.providers.mock import MockMusicProvider
from app.services.search.service import local_search, federated_search
from app.core.playback.resolver import PlaybackResolver
from app.intelligence.vibe.parser import parse_vibe
from app.core.profiles.service import get_or_create_default
from app.core.tracks.service import upsert_provider_track
from app.providers.lyrics.lrclib import LRCLIBProvider
from app.services.recommendations.service import recommend, rebuild_candidates, persisted_recommendations
from app.providers.registry import provider_status
from app.services.sync.service import enqueue_sync, sync_search_query
from app.services.integrations import authorize_url, callback as oauth_callback, statuses as integration_statuses, spotify_library, youtube_library, sync_all_libraries
from app.tools.sync_provider_libraries import materialize_history
from app.core.queue.service import QueueService
from app.services.radio import smart_radio
from app.services.vibe_journey import build_vibe_journey
from app.intelligence.audio.features import analyze_track
from app.services.lyrics.enrichment import enrich_track, enrich_batch
from app.services.lyrics.sync import parse_lrc, active_index
from app.services.local_library import index_paths

settings = get_settings()
app = FastAPI(title="NOMAD Music API", version="0.1.0")

@app.on_event("startup")
def ensure_local_database():
    # Desktop production runs the API as a bundled sidecar and therefore cannot
    # rely on a manually executed Alembic command. Create missing tables at first
    # launch; development still uses Alembic for schema migrations.
    from app.db.models.base import Base
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)

app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://127.0.0.1:1420", "http://localhost:1420", "tauri://localhost", "https://tauri.localhost"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
mock = MockMusicProvider()

def track_out(db: Session, t: Track) -> TrackOut:
    sources = db.query(TrackSource).filter(TrackSource.track_id == t.id).all()
    artist = db.get(__import__("app.db.models", fromlist=["Artist"]).Artist, t.artist_id) if t.artist_id else None
    album = db.get(__import__("app.db.models", fromlist=["Album"]).Album, t.album_id) if t.album_id else None
    return TrackOut(
        id=t.id, title=t.title, duration_ms=t.duration_ms, artwork_url=t.artwork_url,
        artist_id=t.artist_id, artist_name=artist.name if artist else None,
        album_id=t.album_id, album_name=album.title if album else None,
        isrc=t.isrc, sources=[TrackSourceOut.model_validate(s, from_attributes=True) for s in sources]
    )

@app.get("/api/v1/health")
def health():
    return {"ok": True, "service": "nomad-music", "version": app.version}

@app.get("/api/v1/health/providers")
async def provider_health(db: Session = Depends(get_db)):
    configured = {p["name"]: p for p in provider_status()}
    connected = {p["provider"]: p for p in integration_statuses(db)}
    merged = []
    for name, row in configured.items():
        merged.append({**row, **connected.get(name, {})})
    return {"providers": merged}

@app.get("/api/v1/search")
async def search(q: str = Query(min_length=1), limit: int = 20, db: Session = Depends(get_db)):
    local = local_search(db, q, limit=limit)
    results = [{"track": track_out(db, t), "score": 1.0, "source": "local"} for t in local]
    if len(results) < limit:
        for t, source in await federated_search(db, q, limit=limit - len(results)):
            if any(x["track"].id == t.id for x in results):
                continue
            results.append({"track": track_out(db, t), "score": 0.6, "source": source})
    return {"results": results[:limit]}

@app.get("/api/v1/tracks/{track_id}")
def get_track(track_id: str, db: Session = Depends(get_db)):
    t = db.get(Track, track_id)
    if not t: raise HTTPException(404, "track not found")
    return track_out(db, t)

@app.get("/api/v1/tracks/{track_id}/resolve")
def resolve_track(track_id: str, preferred_source: str | None = None, db: Session = Depends(get_db)):
    r = PlaybackResolver(db).resolve(track_id, preferred_provider=preferred_source)
    return r.__dict__


@app.post("/api/v1/library/index")
def index_local_library(root: str, recursive: bool = True, limit: int = 500, db: Session = Depends(get_db)):
    try:
        return {"ok": True, **index_paths(db, root, recursive=recursive, limit=limit)}
    except ValueError as exc:
        raise HTTPException(400, str(exc))

@app.get("/api/v1/tracks/{track_id}/audio")
def local_audio(track_id: str, db: Session = Depends(get_db)):
    source = db.scalar(select(TrackSource).where(TrackSource.track_id == track_id, TrackSource.provider == "local", TrackSource.available.is_(True)))
    if not source or not source.uri:
        raise HTTPException(404, "local audio source not found")
    path = source.uri.replace("file://", "", 1)
    p = __import__("pathlib").Path(path)
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "audio file is unavailable")
    return FileResponse(p)

@app.get("/api/v1/tracks/{track_id}/lyrics/state")
def lyrics_state(track_id: str, db: Session = Depends(get_db)):
    cached = db.scalar(select(Lyrics).where(Lyrics.track_id == track_id))
    return {"indexed": bool(cached and (cached.plain_lyrics or cached.synced_lyrics)), "source": cached.source if cached else None, "offset_ms": cached.offset_ms if cached else 0}

@app.get("/api/v1/tracks/{track_id}/lyrics/sync")
def lyrics_sync(track_id: str, db: Session = Depends(get_db)):
    cached = db.scalar(select(Lyrics).where(Lyrics.track_id == track_id))
    if not cached:
        raise HTTPException(404, "lyrics are not indexed")
    lines = parse_lrc(cached.synced_lyrics)
    return {"found": bool(cached.plain_lyrics or cached.synced_lyrics), "source": cached.source, "offset_ms": cached.offset_ms, "lines": [{"time_ms": x.time_ms, "text": x.text} for x in lines], "plain": cached.plain_lyrics or ""}

@app.post("/api/v1/tracks/{track_id}/lyrics/offset")
def lyrics_offset(track_id: str, offset_ms: int = Query(0, ge=-15000, le=15000), db: Session = Depends(get_db)):
    cached = db.scalar(select(Lyrics).where(Lyrics.track_id == track_id))
    if not cached:
        raise HTTPException(404, "lyrics are not indexed")
    cached.offset_ms = offset_ms
    db.commit()
    return {"ok": True, "offset_ms": offset_ms}

@app.get("/api/v1/library")
def library(limit: int = 100, db: Session = Depends(get_db)):
    rows = db.query(Track).order_by(Track.updated_at.desc()).limit(limit).all()
    return {"tracks": [track_out(db, t) for t in rows]}

@app.get("/api/v1/playlists", response_model=list[PlaylistOut])
def playlists(db: Session = Depends(get_db)):
    out=[]
    for p in db.query(Playlist).order_by(Playlist.updated_at.desc()).all():
        items = db.query(PlaylistItem).filter(PlaylistItem.playlist_id==p.id).order_by(PlaylistItem.position).all()
        tracks=[track_out(db, db.get(Track, i.track_id)) for i in items if db.get(Track, i.track_id)]
        out.append(PlaylistOut(id=p.id,name=p.name,description=p.description,artwork_url=p.artwork_url,tracks=tracks))
    return out

@app.post("/api/v1/playlists", response_model=PlaylistOut)
def create_playlist(payload: PlaylistCreate, db: Session = Depends(get_db)):
    p=Playlist(name=payload.name, description=payload.description); db.add(p); db.commit(); db.refresh(p)
    return PlaylistOut(id=p.id,name=p.name,description=p.description,artwork_url=p.artwork_url,tracks=[])

@app.get("/api/v1/playlists/{playlist_id}", response_model=PlaylistOut)
def get_playlist(playlist_id: str, db: Session = Depends(get_db)):
    p = db.get(Playlist, playlist_id)
    if not p:
        raise HTTPException(404, "playlist not found")
    items = db.query(PlaylistItem).filter(PlaylistItem.playlist_id == p.id).order_by(PlaylistItem.position).all()
    tracks = [track_out(db, db.get(Track, i.track_id)) for i in items if db.get(Track, i.track_id)]
    return PlaylistOut(id=p.id, name=p.name, description=p.description, artwork_url=p.artwork_url, tracks=tracks)

@app.patch("/api/v1/playlists/{playlist_id}")
def update_playlist(playlist_id: str, payload: PlaylistCreate, db: Session = Depends(get_db)):
    p = db.get(Playlist, playlist_id)
    if not p:
        raise HTTPException(404, "playlist not found")
    p.name = payload.name
    p.description = payload.description
    db.commit()
    return {"ok": True}

@app.post("/api/v1/playlists/{playlist_id}/reorder")
def reorder_playlist(playlist_id: str, item_ids: list[str], db: Session = Depends(get_db)):
    items = db.query(PlaylistItem).filter(PlaylistItem.playlist_id == playlist_id).all()
    by_id = {i.id: i for i in items}
    if set(item_ids) != set(by_id):
        raise HTTPException(400, "item_ids must contain exactly the playlist item ids")
    for pos, item_id in enumerate(item_ids):
        by_id[item_id].position = pos
    db.commit()
    return {"ok": True, "count": len(item_ids)}

@app.get("/api/v1/playlists/{playlist_id}/doctor")
def playlist_doctor(playlist_id: str, db: Session = Depends(get_db)):
    p = db.get(Playlist, playlist_id)
    if not p:
        raise HTTPException(404, "playlist not found")
    items = db.query(PlaylistItem).filter(PlaylistItem.playlist_id == playlist_id).order_by(PlaylistItem.position).all()
    tracks = [db.get(Track, i.track_id) for i in items]
    seen = set(); duplicates = []; missing = []; artists = {}
    for t in tracks:
        if not t:
            missing.append("deleted-track")
            continue
        key = t.normalized_title
        if key in seen:
            duplicates.append(t.id)
        seen.add(key)
    return {"playlist_id": playlist_id, "tracks": len(tracks), "duplicates": duplicates, "missing": missing, "duplicate_count": len(duplicates)}

@app.post("/api/v1/events/{event_type}")
def event(event_type: str, payload: EventIn, db: Session = Depends(get_db)):
    if event_type not in {"play","skip","like","dislike","replay","search"}:
        raise HTTPException(400,"unsupported event")
    if event_type in {"play","skip","replay"}:
        db.add(PlayEvent(track_id=payload.track_id, profile_id=payload.profile_id, seconds=payload.seconds, event_type=event_type)); db.commit()
    return {"ok": True}

@app.get("/api/v1/player/queue")
def player_queue(profile_id: str = "default", db: Session = Depends(get_db)):
    return QueueService(db).get(profile_id).__dict__

@app.put("/api/v1/player/queue")
def replace_player_queue(track_ids: list[str], profile_id: str = "default", start_index: int = 0, db: Session = Depends(get_db)):
    missing = [tid for tid in track_ids if not db.get(Track, tid)]
    if missing:
        raise HTTPException(404, f"tracks not found: {', '.join(missing[:5])}")
    return QueueService(db).replace(profile_id, track_ids, start_index).__dict__

@app.patch("/api/v1/player/state")
def update_player_state(profile_id: str = "default", current_item_id: str | None = None, is_playing: bool | None = None, position_ms: int | None = None, volume: float | None = None, shuffle: bool | None = None, repeat: str | None = None, db: Session = Depends(get_db)):
    if volume is not None and not 0 <= volume <= 1: raise HTTPException(400, "volume must be between 0 and 1")
    if repeat is not None and repeat not in {"off", "one", "all"}: raise HTTPException(400, "repeat must be off, one, or all")
    return QueueService(db).set_state(profile_id, current_item_id=current_item_id, is_playing=is_playing, position_ms=position_ms, volume=volume, shuffle=shuffle, repeat=repeat).__dict__

@app.post("/api/v1/player/next")
def player_next(profile_id: str = "default", db: Session = Depends(get_db)):
    return QueueService(db).next(profile_id).__dict__

@app.post("/api/v1/player/previous")
def player_previous(profile_id: str = "default", db: Session = Depends(get_db)):
    return QueueService(db).previous(profile_id).__dict__

@app.get("/api/v1/vibe")
def vibe(q: str = Query(min_length=1)):
    return {"query": parse_vibe(q).model_dump()}

@app.get("/api/v1/profiles")
def profiles(db: Session = Depends(get_db)):
    rows = db.query(Profile).order_by(Profile.created_at).all()
    return {"profiles": [{"id": p.id, "name": p.name, "is_default": p.is_default} for p in rows]}

@app.post("/api/v1/profiles")
def create_profile(name: str = Query(min_length=1, max_length=200), db: Session = Depends(get_db)):
    p = Profile(name=name, is_default=False); db.add(p); db.commit(); db.refresh(p)
    return {"id": p.id, "name": p.name, "is_default": p.is_default}

@app.post("/api/v1/playlists/{playlist_id}/items")
def add_playlist_item(playlist_id: str, track_id: str, preferred_source: str | None = None, db: Session = Depends(get_db)):
    if not db.get(Playlist, playlist_id) or not db.get(Track, track_id):
        raise HTTPException(404, "playlist or track not found")
    last = db.query(PlaylistItem).filter(PlaylistItem.playlist_id == playlist_id).order_by(PlaylistItem.position.desc()).first()
    position = (last.position + 1) if last else 0
    item = PlaylistItem(playlist_id=playlist_id, track_id=track_id, position=position, preferred_source=preferred_source)
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "playlist_id": playlist_id, "track_id": track_id, "position": position}

@app.delete("/api/v1/playlists/{playlist_id}/items/{item_id}")
def remove_playlist_item(playlist_id: str, item_id: str, db: Session = Depends(get_db)):
    item = db.query(PlaylistItem).filter(PlaylistItem.id == item_id, PlaylistItem.playlist_id == playlist_id).first()
    if not item: raise HTTPException(404, "playlist item not found")
    db.delete(item); db.commit(); return {"ok": True}

@app.post("/api/v1/signals")
def signal(payload: EventIn, db: Session = Depends(get_db)):
    profile = payload.profile_id or get_or_create_default(db).id
    if payload.track_id and not db.get(Track, payload.track_id): raise HTTPException(404, "track not found")
    db.add(UserSignal(profile_id=profile, track_id=payload.track_id, signal=payload.event_type, value=max(0.0, float(payload.seconds or 1))))
    db.commit(); return {"ok": True, "profile_id": profile}

@app.post("/api/v1/tracks/{track_id}/favorite")
def favorite_track(track_id: str, liked: bool = True, profile_id: str = "default", db: Session = Depends(get_db)):
    if not db.get(Track, track_id):
        raise HTTPException(404, "track not found")
    db.add(UserSignal(profile_id=profile_id, track_id=track_id, signal="like" if liked else "dislike", value=1.0))
    db.commit()
    return {"ok": True, "liked": liked}

@app.post("/api/v1/tracks/import/mock")
def import_mock(query: str, db: Session = Depends(get_db)):
    rows = __import__("asyncio").run(mock.search(query, limit=5))
    tracks = [upsert_provider_track(db, item) for item in rows]
    return {"tracks": [track_out(db, t) for t in tracks]}

@app.post("/api/v1/search/sync")
async def sync_search(query: str = Query(min_length=1, max_length=300), provider: str | None = None, limit: int = 30, db: Session = Depends(get_db)):
    return await sync_search_query(db, query=query, provider_name=provider, limit=max(1, min(limit, 50)))

@app.post("/api/v1/sync/jobs")
def create_sync_job(provider: str | None = None, query: str | None = None, db: Session = Depends(get_db)):
    job = enqueue_sync(db, provider=provider, query=query)
    return {"queued": True, "job_id": job.id, "provider": provider, "query": query}

@app.get("/api/v1/tracks/{track_id}/features")
def track_features(track_id: str, force: bool = False, db: Session = Depends(get_db)):
    row = analyze_track(db, track_id, force=force)
    if not row:
        raise HTTPException(404, "track not found")
    return {"track_id": track_id, "model_version": row.model_version, "bpm": row.bpm, "key": row.key, "energy": row.energy, "danceability": row.danceability, "acousticness": row.acousticness, "loudness": row.loudness, "mood": row.mood, "source": row.source}

@app.post("/api/v1/tracks/{track_id}/lyrics/prefetch")
async def prefetch_lyrics(track_id: str, db: Session = Depends(get_db)):
    return await enrich_track(db, track_id)

@app.post("/api/v1/lyrics/prefetch")
async def prefetch_lyrics_batch(limit: int = 10, db: Session = Depends(get_db)):
    return {"results": await enrich_batch(db, max(1, min(limit, 25)))}

@app.get("/api/v1/tracks/{track_id}/lyrics")
async def get_lyrics(track_id: str, refresh: bool = False, db: Session = Depends(get_db)):
    t = db.get(Track, track_id)
    if not t:
        raise HTTPException(404, "track not found")
    cached = db.scalar(__import__("sqlalchemy").select(Lyrics).where(Lyrics.track_id == track_id))
    if not cached or refresh or not (cached.plain_lyrics or cached.synced_lyrics):
        artist = db.get(__import__("app.db.models", fromlist=["Artist"]).Artist, t.artist_id)
        result = await LRCLIBProvider().search(t.title, artist.name if artist else "", t.duration_ms)
        if result:
            if not cached:
                cached = Lyrics(track_id=track_id)
                db.add(cached)
            cached.plain_lyrics = result.get("plain", "")
            cached.synced_lyrics = result.get("synced", "")
            cached.source = result.get("source")
            db.commit()
    if not cached:
        return {"found": False, "plain": "", "synced": "", "source": None, "lines": []}
    lines = parse_lrc(cached.synced_lyrics)
    return {"found": bool(cached.plain_lyrics or cached.synced_lyrics), "source": cached.source, "plain": cached.plain_lyrics or "", "synced": cached.synced_lyrics or "", "offset_ms": cached.offset_ms, "lines": [{"time_ms": x.time_ms, "text": x.text} for x in lines]}

@app.get("/api/v1/radio")
def radio(profile_id: str | None = None, seed_track_id: str | None = None, limit: int = 20, db: Session = Depends(get_db)):
    return {"mode": "smart_radio", "seed_track_id": seed_track_id, "tracks": smart_radio(db, profile_id, seed_track_id, max(1, min(limit, 50)))}

@app.get("/api/v1/vibe/journey")
def vibe_journey(target_minutes: int = 45, limit: int = 30, db: Session = Depends(get_db)):
    return {"mode": "vibe_journey", "target_minutes": target_minutes, "tracks": build_vibe_journey(db, max(5, min(target_minutes, 240)), max(5, min(limit, 50)))}

@app.post("/api/v1/player/smart-extend")
def player_smart_extend(profile_id: str = "default", count: int = 5, db: Session = Depends(get_db)):
    return QueueService(db).smart_extend(profile_id, max(1, min(count, 20))).__dict__

@app.get("/api/v1/recommendations")
def recommendations(profile_id: str | None = None, limit: int = 20, db: Session = Depends(get_db)):
    rows = persisted_recommendations(db, profile_id=profile_id, limit=max(1, min(limit, 100)))
    if not rows:
        rebuild_candidates(db, profile_id, limit=100)
        rows = persisted_recommendations(db, profile_id=profile_id, limit=max(1, min(limit, 100)))
    return {"results": [{"track_id": r.track_id, "score": round(r.score, 4), "reason": json.loads(r.reason_json or "{}")} for r in rows]}

@app.post("/api/v1/jobs/recommendations")
def queue_recommendations(profile_id: str | None = None, db: Session = Depends(get_db)):
    job = BackgroundJob(job_type="rebuild_recommendations", status="queued", priority=80, payload_json=json.dumps({"profile_id": profile_id}))
    db.add(job); db.commit(); db.refresh(job)
    return {"queued": True, "job_id": job.id}

@app.get("/api/v1/events/stream")
async def events_stream():
    async def gen():
        yield f"data: {json.dumps({'type':'ready'})}\n\n"
        while True:
            await asyncio.sleep(20)
            yield f"data: {json.dumps({'type':'heartbeat'})}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/api/v1/integrations/spotify/player-token")
async def spotify_player_token(profile_id: str | None = None, db: Session = Depends(get_db)):
    profile = get_or_create_default(db) if not profile_id else db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(404, "profile not found")
    try:
        from app.providers.spotify.session import get_spotify_access_token
        token = await get_spotify_access_token(db, profile.id)
    except Exception as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "access_token": token}

@app.get("/api/v1/integrations/connections")
def integration_connections(db: Session = Depends(get_db)):
    return {"connections": integration_statuses(db)}

@app.get("/api/v1/integrations/{provider}/authorize")
def integration_authorize(provider: str, profile_id: str | None = None, db: Session = Depends(get_db)):
    profile=get_or_create_default(db) if not profile_id else db.get(Profile,profile_id)
    if not profile: raise HTTPException(404,"profile not found")
    try: url=authorize_url(db,provider,profile.id)
    except Exception as exc: raise HTTPException(400,str(exc))
    return {"provider":provider,"profile_id":profile.id,"authorization_url":url}

@app.get("/api/v1/integrations/{provider}/callback")
async def integration_callback(provider: str, code: str | None = None, state: str | None = None, db: Session = Depends(get_db)):
    if not code or not state: raise HTTPException(400,"code and state are required")
    try:
        acc=await oauth_callback(db,provider,code,state)
    except Exception as exc:
        raise HTTPException(400,str(exc))
    # A successful connect is exactly when the user expects their library/
    # history to start showing real data - previously this required manually
    # running `python -m app.tools.sync_provider_libraries` from a terminal,
    # which nothing in the app ever told the user to do. Sync right away so
    # connecting actually produces visible results instead of silently doing
    # nothing until someone stumbles onto the CLI script.
    try:
        profile = get_or_create_default(db)
        sync_result = await sync_all_libraries(db, profile.id)
        materialize_history(db, profile.id)
    except Exception:
        sync_result = None
    status_line = "Your library and history are syncing now." if sync_result and sync_result.get("ok") else "Connected. Library sync will retry automatically."
    return HTMLResponse(f"""<!doctype html><html><body style='font-family:Arial;background:#0b0c10;color:#eee;display:grid;place-items:center;height:100vh'><div style='text-align:center'><h2>NOMAD connected</h2><p>{provider.title()} account connected. {status_line}</p><script>setTimeout(()=>window.close(),1200)</script></div></body></html>""")


@app.post("/api/v1/integrations/sync")
async def integration_sync_all(db: Session = Depends(get_db)):
    """Manual re-sync trigger for the Source Hub 'Sync Library' button, and
    a fallback for anyone who connected before this ran automatically."""
    profile = get_or_create_default(db)
    result = await sync_all_libraries(db, profile.id)
    result["history"] = materialize_history(db, profile.id)
    return result


@app.post("/api/v1/integrations/spotify/library")
async def spotify_library_mutate(payload: dict, profile_id: str = "default", db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id) or get_or_create_default(db)
    uris = [str(x).strip() for x in (payload.get("uris") or []) if str(x).strip()]
    action = str(payload.get("action") or "save").lower()
    if action not in {"save", "remove"}:
        raise HTTPException(400, "action must be save or remove")
    from app.services.integrations import spotify_library_mutation
    try:
        return await spotify_library_mutation(db, profile.id, uris, remove=action == "remove")
    except Exception as exc:
        raise HTTPException(400, str(exc))

@app.get("/api/v1/integrations/spotify/library/contains")
async def spotify_library_contains(uris: list[str] = Query(default=[]), profile_id: str = "default", db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id) or get_or_create_default(db)
    from app.services.integrations import spotify_library_contains as _contains
    try:
        return await _contains(db, profile.id, [str(x).strip() for x in uris if str(x).strip()])
    except Exception as exc:
        raise HTTPException(400, str(exc))

@app.get("/api/v1/tracks/{track_id}/playback")
def track_playback(track_id: str, db: Session = Depends(get_db)):
    r=PlaybackResolver(db).resolve(track_id)
    return {"track_id":track_id, **r.__dict__}
@app.post("/api/v1/integrations/{provider}/sync")
async def integration_sync(provider: str, profile_id: str = "default", db: Session = Depends(get_db)):
    profile = db.get(Profile, profile_id)
    if not profile:
        profile = get_or_create_default(db)
    try:
        if provider == "spotify":
            result = await spotify_library(db, profile.id)
        elif provider == "youtube":
            result = await youtube_library(db, profile.id)
        else:
            raise ValueError("sync supported for spotify or youtube")
    except Exception as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True, "profile_id": profile.id, **result}

@app.post("/api/v1/player/smart-extend")
def smart_extend_queue(profile_id: str = "default", count: int = 5, db: Session = Depends(get_db)):
    if count < 1 or count > 25:
        raise HTTPException(400, "count must be 1..25")
    return QueueService(db).smart_extend(profile_id, count).__dict__


