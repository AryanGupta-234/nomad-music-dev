import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from sqlalchemy.orm import Session
from app.db.session import engine
from app.db.models import BackgroundJob
from app.config.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nomad-worker")


def enqueue(job_type: str, priority: int = 50, payload: dict | None = None):
    import json
    with Session(engine) as db:
        db.add(BackgroundJob(job_type=job_type, status="queued", priority=priority, payload_json=json.dumps(payload or {})))
        db.commit()
    log.info("queued %s", job_type)


def process_jobs():
    from app.workers.run_once import run
    run()


def main():
    settings = get_settings()
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(process_jobs, "interval", seconds=30, id="process_jobs", max_instances=1, coalesce=True)
    scheduler.add_job(lambda: enqueue("sync_spotify", 90), "interval", hours=6, id="spotify_sync", max_instances=1, coalesce=True)
    scheduler.add_job(lambda: enqueue("sync_youtube", 90), "interval", hours=6, id="youtube_sync", max_instances=1, coalesce=True)
    scheduler.add_job(lambda: enqueue("enrich_lyrics", 70, {"limit": 10}), "interval", hours=1, id="lyrics", max_instances=1, coalesce=True)
    scheduler.add_job(lambda: enqueue("rebuild_recommendations", 80), "interval", hours=1, id="recommendations", max_instances=1, coalesce=True)
    scheduler.add_job(lambda: enqueue("refresh_discovery", 50), "interval", minutes=30, id="discovery", max_instances=1, coalesce=True)
    log.info("NOMAD worker started (env=%s)", settings.app_env)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown(wait=False)

if __name__ == "__main__":
    main()
