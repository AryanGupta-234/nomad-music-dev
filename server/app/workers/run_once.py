import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.session import engine
from app.db.models import BackgroundJob
from app.services.recommendations.service import rebuild_candidates
from app.services.lyrics.enrichment import enrich_batch
from app.intelligence.audio.features import analyze_track


def _finish(job, status="success", error=None):
    job.status=status; job.error=error; job.finished_at=datetime.now(timezone.utc)


def run():
    with Session(engine) as db:
        rows=db.query(BackgroundJob).filter(BackgroundJob.status=="queued").order_by(BackgroundJob.priority.desc(), BackgroundJob.created_at).limit(20).all()
        for job in rows:
            job.status="running"; job.attempts+=1; job.started_at=datetime.now(timezone.utc); db.commit()
            try:
                payload=json.loads(job.payload_json or "{}")
                if job.job_type=="rebuild_recommendations":
                    rebuild_candidates(db, profile_id=payload.get("profile_id"), limit=100)
                elif job.job_type=="enrich_lyrics":
                    import asyncio
                    asyncio.run(enrich_batch(db, limit=int(payload.get("limit", 10))))
                elif job.job_type=="analyze_audio":
                    ids=payload.get("track_ids") or []
                    for tid in ids[:25]: analyze_track(db, tid, force=bool(payload.get("force")))
                elif job.job_type in {"sync_spotify", "sync_youtube"}:
                    _finish(job, "deferred", "waiting for authenticated sync runner")
                elif job.job_type=="refresh_discovery":
                    pass
                if job.status=="running": _finish(job, "success")
                db.commit()
            except Exception as exc:
                _finish(job, "failed", str(exc)); db.commit()
