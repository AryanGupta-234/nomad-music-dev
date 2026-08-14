import json
from datetime import datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.db.models import Track, UserSignal, RecommendationCandidate, Profile
from app.intelligence.recommender.engine import Candidate, rank

POSITIVE = {"like": 1.0, "replay": 0.8, "play_complete": 0.5, "playlist_add": 0.7, "play": 0.15}
NEGATIVE = {"dislike": 1.0, "skip": 0.7, "playlist_remove": 0.4}


def build_profile_scores(db: Session, profile_id: str | None):
    stmt = select(UserSignal)
    if profile_id:
        stmt = stmt.where(UserSignal.profile_id == profile_id)
    rows = db.scalars(stmt).all()
    scores = {}
    skips = {}
    for r in rows:
        score = POSITIVE.get(r.signal, 0.0) - NEGATIVE.get(r.signal, 0.0)
        scores[r.track_id] = scores.get(r.track_id, 0.0) + score * max(1.0, r.value)
        if r.signal in {"skip", "dislike"}:
            skips[r.track_id] = skips.get(r.track_id, 0.0) + max(1.0, r.value)
    return scores, skips


def recommend(db: Session, profile_id: str | None = None, limit: int = 20):
    profile = profile_id or _default_profile_id(db)
    tracks = db.scalars(select(Track)).all()
    profile_scores, skip_scores = build_profile_scores(db, profile)
    recent_ids = set(
        db.scalars(
            select(UserSignal.track_id)
            .where(UserSignal.profile_id == profile, UserSignal.signal == "play")
            .order_by(UserSignal.created_at.desc()).limit(12)
        ).all()
    ) if profile else set()
    candidates = []
    for t in tracks:
        raw = profile_scores.get(t.id, 0.0)
        similarity = max(0.0, min(1.0, 0.5 + raw * 0.08))
        repetition = 1.0 if t.id in recent_ids else 0.0
        skip_penalty = max(0.0, min(1.0, skip_scores.get(t.id, 0.0) * 0.2))
        freshness = 0.15
        novelty = 0.25 if raw <= 0 else 0.12
        candidates.append(Candidate(t.id, similarity, freshness, novelty, repetition, skip_penalty))
    return rank(candidates)[:limit]


def rebuild_candidates(db: Session, profile_id: str | None, limit: int = 100):
    profile = profile_id or _default_profile_id(db)
    if not profile:
        return []
    rows = recommend(db, profile, limit=limit)
    db.execute(delete(RecommendationCandidate).where(RecommendationCandidate.profile_id == profile))
    now = datetime.now(timezone.utc)
    for candidate, score in rows:
        db.add(RecommendationCandidate(
            profile_id=profile,
            track_id=candidate.track_id,
            score=score,
            reason_json=json.dumps({
                "similarity": candidate.similarity,
                "freshness": candidate.freshness,
                "novelty": candidate.novelty,
                "repetition_penalty": candidate.repetition_penalty,
                "skip_penalty": candidate.skip_penalty,
            }),
            generated_at=now,
        ))
    db.commit()
    return rows


def persisted_recommendations(db: Session, profile_id: str | None, limit: int = 20):
    profile = profile_id or _default_profile_id(db)
    if not profile:
        return []
    rows = db.scalars(
        select(RecommendationCandidate)
        .where(RecommendationCandidate.profile_id == profile)
        .order_by(RecommendationCandidate.score.desc(), RecommendationCandidate.generated_at.desc())
        .limit(limit)
    ).all()
    return rows


def _default_profile_id(db: Session):
    p = db.scalar(select(Profile).where(Profile.is_default == True))
    return p.id if p else None
