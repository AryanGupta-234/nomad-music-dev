from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.tracks.service import upsert_provider_track
from app.db.models import BackgroundJob, ProviderSyncState, TrackSource
from app.providers.registry import music_providers


def enqueue_sync(db: Session, provider: str | None = None, query: str | None = None, priority: int = 80) -> BackgroundJob:
    job = BackgroundJob(
        job_type="sync_provider",
        status="queued",
        priority=priority,
        payload_json=json.dumps({"provider": provider, "query": query}),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


async def sync_search_query(db: Session, query: str, provider_name: str | None = None, limit: int = 50) -> dict:
    providers = [p for p in music_providers() if not provider_name or p.name == provider_name]
    imported = 0
    updated = 0
    failures: list[dict] = []

    for provider in providers:
        try:
            rows = await provider.search(query, limit=min(limit, 50))
            for item in rows:
                existing = db.scalar(select(TrackSource).where(
                    TrackSource.provider == item.provider,
                    TrackSource.provider_id == item.provider_id,
                ))
                upsert_provider_track(db, item)
                if existing:
                    updated += 1
                else:
                    imported += 1
            _mark_success(db, provider.name, f"search:{query}")
        except Exception as exc:
            failures.append({"provider": provider.name, "error": str(exc)})
            _mark_error(db, provider.name, f"search:{query}", str(exc))
    return {
        "query": query,
        "providers": [p.name for p in providers],
        "imported": imported,
        "updated": updated,
        "failed": failures,
    }


def _mark_success(db: Session, provider: str, resource: str) -> None:
    state = db.scalar(select(ProviderSyncState).where(
        ProviderSyncState.provider == provider,
        ProviderSyncState.resource == resource,
        ProviderSyncState.profile_id.is_(None),
    ))
    if not state:
        state = ProviderSyncState(provider=provider, resource=resource)
        db.add(state)
    state.last_success_at = datetime.now(timezone.utc)
    state.last_error = None
    db.commit()


def _mark_error(db: Session, provider: str, resource: str, error: str) -> None:
    state = db.scalar(select(ProviderSyncState).where(
        ProviderSyncState.provider == provider,
        ProviderSyncState.resource == resource,
        ProviderSyncState.profile_id.is_(None),
    ))
    if not state:
        state = ProviderSyncState(provider=provider, resource=resource)
        db.add(state)
    state.last_error = error[:2000]
    db.commit()
