"""NOMAD V4 local stability doctor.

Run from server/:
    python -m app.tools.doctor_v4

This is intentionally read-only. It checks the local database, provider
configuration, OAuth connection state, and the key provider sync entrypoints
without making network mutations or changing user data.
"""
from __future__ import annotations

import asyncio
import importlib

from sqlalchemy import select

from app.config.settings import get_settings
from app.core.profiles.service import get_or_create_default
from app.db.models import IntegrationAccount, PlayEvent, Playlist, Track, TrackSource
from app.db.session import SessionLocal
from app.providers.registry import provider_status


def main() -> int:
    settings = get_settings()
    db = SessionLocal()
    failures = 0
    try:
        profile = get_or_create_default(db)
        tracks = db.scalar(select(Track).count()) if False else len(db.scalars(select(Track)).all())
        sources = len(db.scalars(select(TrackSource)).all())
        playlists = len(db.scalars(select(Playlist)).all())
        events = len(db.scalars(select(PlayEvent).where(PlayEvent.profile_id == profile.id)).all())
        accounts = {a.provider: a for a in db.scalars(select(IntegrationAccount)).all()}

        print("NOMAD V4 stability doctor")
        print(f"profile: {profile.id} ({profile.name})")
        print(f"database: tracks={tracks} sources={sources} playlists={playlists} play_events={events}")

        configured = {p["name"]: p for p in provider_status()}
        for name in ("spotify", "youtube"):
            cfg = configured.get(name, {})
            acc = accounts.get(name)
            connected = bool(acc and acc.access_token)
            print(f"{name}: configured={bool(cfg.get('configured'))} connected={connected}")
            if bool(cfg.get("configured")) and not connected:
                print(f"  - action: open NOMAD Source Hub and connect {name}")

        try:
            integrations = importlib.import_module("app.services.integrations")
            for fn in ("spotify_library", "youtube_library", "sync_all_libraries"):
                if not callable(getattr(integrations, fn, None)):
                    print(f"FAIL: missing integration function {fn}")
                    failures += 1
        except Exception as exc:
            print(f"FAIL: integration module import: {type(exc).__name__}: {exc}")
            failures += 1

        if not tracks:
            print("WARN: no tracks are indexed/imported yet")
        if not playlists:
            print("WARN: no playlists exist yet")

        print("result: PASS" if failures == 0 else f"result: FAIL ({failures} checks)")
        return failures
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
