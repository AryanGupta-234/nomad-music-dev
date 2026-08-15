import json
from datetime import datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.orm import Session
from app.db.models import Track, UserSignal, RecommendationCandidate, Profile, PlaylistItem, ExternalCollection, AudioFeature, TrackEmbedding
from app.intelligence.recommender.engine import Candidate, cosine, rank

POSITIVE = {"like": 1.0, "replay": 0.8, "play_complete": 0.5, "playlist_add": 0.7, "play": 0.15}
NEGATIVE = {"dislike": 1.0, "skip": 0.7, "playlist_remove": 0.4}


def build_profile_scores(db: Session, profile_id: str | None):
    scores, skips = {}, {}
    stmt = select(UserSignal)
    if profile_id:
        stmt = stmt.where(UserSignal.profile_id == profile_id)
    for r in db.scalars(stmt).all():
        score = POSITIVE.get(r.signal, 0.0) - NEGATIVE.get(r.signal, 0.0)
        scores[r.track_id] = scores.get(r.track_id, 0.0) + score * max(1.0, r.value)
        if r.signal in {"skip", "dislike"}:
            skips[r.track_id] = skips.get(r.track_id, 0.0) + max(1.0, r.value)

    # Imported Spotify/YouTube collections are real taste signals even before
    # the user has generated NOMAD play/like events.
    if profile_id:
        rows = db.execute(
            select(PlaylistItem.track_id, ExternalCollection.kind)
            .join(ExternalCollection, ExternalCollection.local_playlist_id == PlaylistItem.playlist_id)
            .where(ExternalCollection.profile_id == profile_id)
        ).all()
        for track_id, kind in rows:
            scores[track_id] = scores.get(track_id, 0.0) + (1.0 if kind == "liked" else 0.45)
    return scores, skips


def _feature_vector(feature: AudioFeature | None) -> list[float] | None:
    if not feature:
        return None
    values = [
        (feature.bpm or 0.0) / 200.0,
        feature.energy or 0.0,
        feature.danceability or 0.0,
        feature.acousticness or 0.0,
        # Loudness is commonly negative dB; clamp it into a stable 0..1 range.
        max(0.0, min(1.0, ((feature.loudness or -60.0) + 60.0) / 60.0)),
    ]
    return values if any(values) else None


def _profile_audio_vector(db: Session, profile_scores: dict[str, float]) -> list[float] | None:
    if not profile_scores:
        return None
    ids = [tid for tid, score in profile_scores.items() if score > 0]
    if not ids:
        return None
    rows = db.scalars(select(AudioFeature).where(AudioFeature.track_id.in_(ids))).all()
    weighted: list[float] | None = None
    total = 0.0
    for row in rows:
        vec = _feature_vector(row)
        weight = max(0.1, profile_scores.get(row.track_id, 0.0))
        if not vec:
            continue
        if weighted is None:
            weighted = [0.0] * len(vec)
        for i, value in enumerate(vec):
            weighted[i] += value * weight
        total += weight
    if not weighted or not total:
        return None
    return [value / total for value in weighted]


def _embedding_similarity_map(db: Session, profile_scores: dict[str, float], tracks: list[Track]) -> dict[str, float]:
    """Use stored embeddings when available, without making embeddings mandatory."""
    positive_ids = [tid for tid, score in profile_scores.items() if score > 0]
    if not positive_ids:
        return {}
    rows = db.scalars(select(TrackEmbedding).where(TrackEmbedding.track_id.in_(positive_ids))).all()
    if not rows:
        return {}
    profile_vectors = []
    weights = []
    for row in rows:
        try:
            vector = json.loads(row.vector_json)
            if isinstance(vector, list) and vector:
                profile_vectors.append(vector)
                weights.append(max(0.1, profile_scores.get(row.track_id, 0.1)))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    if not profile_vectors:
        return {}
    dims = len(profile_vectors[0])
    if any(len(v) != dims for v in profile_vectors):
        return {}
    profile = [sum(v[i] * w for v, w in zip(profile_vectors, weights)) / sum(weights) for i in range(dims)]
    result = {}
    candidates = db.scalars(select(TrackEmbedding).where(TrackEmbedding.track_id.in_([t.id for t in tracks]))).all()
    for row in candidates:
        try:
            vector = json.loads(row.vector_json)
            if isinstance(vector, list) and len(vector) == dims:
                result[row.track_id] = max(0.0, cosine(profile, vector))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return result


def recommend(db: Session, profile_id: str | None = None, limit: int = 20):
    profile = profile_id or _default_profile_id(db)
    tracks = db.scalars(select(Track)).all()
    profile_scores, skip_scores = build_profile_scores(db, profile)
    audio_profile = _profile_audio_vector(db, profile_scores)
    embedding_scores = _embedding_similarity_map(db, profile_scores, tracks)

    feature_rows = db.scalars(select(AudioFeature).where(AudioFeature.track_id.in_([t.id for t in tracks]))).all()
    feature_map = {row.track_id: row for row in feature_rows}

    recent_ids = set()
    if profile:
        recent_ids = set(db.scalars(
            select(UserSignal.track_id)
            .where(UserSignal.profile_id == profile, UserSignal.signal.in_(["play", "replay"]))
            .order_by(UserSignal.created_at.desc())
            .limit(12)
        ).all())

    candidates = []
    for t in tracks:
        raw = profile_scores.get(t.id, 0.0)
        behavior_similarity = max(0.0, min(1.0, 0.5 + raw * 0.08))
        feature_similarity = 0.0
        if audio_profile:
            vector = _feature_vector(feature_map.get(t.id))
            if vector:
                feature_similarity = max(0.0, cosine(audio_profile, vector))
        embedding_similarity = embedding_scores.get(t.id, 0.0)
        similarity = min(1.0, (0.50 * behavior_similarity) + (0.30 * feature_similarity) + (0.20 * embedding_similarity))
        repetition = 1.0 if t.id in recent_ids else 0.0
        skip_penalty = max(0.0, min(1.0, skip_scores.get(t.id, 0.0) * 0.2))
        freshness = 0.15
        novelty = 0.25 if raw <= 0 else 0.12
        candidates.append(Candidate(t.id, similarity, freshness, novelty, repetition, skip_penalty))

    ranked = rank(candidates)
    # Avoid returning a wall of tracks the user already strongly disliked.
    ranked = [item for item in ranked if skip_scores.get(item[0].track_id, 0.0) < 3.0]
    return ranked[:limit]


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
                "provider_collection_signal": candidate.similarity > 0.5,
            }),
            generated_at=now,
        ))
    db.commit()
    return rows


def persisted_recommendations(db: Session, profile_id: str | None, limit: int = 20):
    profile = profile_id or _default_profile_id(db)
    if not profile:
        return []
    return db.scalars(
        select(RecommendationCandidate)
        .where(RecommendationCandidate.profile_id == profile)
        .order_by(RecommendationCandidate.score.desc(), RecommendationCandidate.generated_at.desc())
        .limit(limit)
    ).all()


def _default_profile_id(db: Session):
    p = db.scalar(select(Profile).where(Profile.is_default == True))
    return p.id if p else None
