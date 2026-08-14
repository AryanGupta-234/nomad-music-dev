# Recommendation Engine

The recommender is not an LLM.

## Signals

- user taste similarity
- vibe similarity
- artist similarity
- genre similarity
- freshness
- exploration/novelty
- context
- skip and repetition penalties

## Pipeline

```text
User/context -> candidate retrieval -> scoring -> diversity -> sequencing -> queue
```

The starter engine is intentionally deterministic and testable. It will later accept learned weights/embeddings without changing the API.
