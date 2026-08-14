from dataclasses import dataclass
from math import sqrt

@dataclass
class Candidate:
    track_id: str
    similarity: float
    freshness: float = 0.0
    novelty: float = 0.0
    repetition_penalty: float = 0.0
    skip_penalty: float = 0.0

def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x*y for x,y in zip(a,b))
    na = sqrt(sum(x*x for x in a)); nb = sqrt(sum(x*x for x in b))
    return dot/(na*nb) if na and nb else 0.0

def score_candidate(c: Candidate) -> float:
    return (0.55 * c.similarity) + (0.15 * c.freshness) + (0.15 * c.novelty) - (0.10 * c.repetition_penalty) - (0.05 * c.skip_penalty)

def rank(candidates: list[Candidate]) -> list[tuple[Candidate, float]]:
    scored = [(c, score_candidate(c)) for c in candidates]
    return sorted(scored, key=lambda x: x[1], reverse=True)
