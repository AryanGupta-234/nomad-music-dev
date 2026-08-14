# AI Architecture

The LLM is the natural-language controller, not the music recommender.

```text
user text
  -> intent parser
  -> structured VibeQuery
  -> recommendation engine
  -> sequence engine
  -> action/explanation
```

Planned actions:

- create playlist
- refine playlist
- explain recommendation
- explain lyrics
- modify queue
- generate Vibe Journey
- AI DJ narration

The system must work with AI disabled; rule-based intent extraction is a valid fallback.
