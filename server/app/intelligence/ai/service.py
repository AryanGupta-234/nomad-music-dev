from app.intelligence.vibe.parser import parse_vibe

class AIService:
    def __init__(self, provider=None):
        self.provider = provider

    async def interpret(self, text: str):
        # Deterministic fallback is always available. A real LLM provider can
        # later replace/augment this method without changing API contracts.
        query = parse_vibe(text)
        return {"vibe": query.model_dump(), "llm_used": bool(self.provider)}
