from app.domain.interfaces.llm_provider import LLMProvider
from app.infrastructure.llm.ollama_provider import OllamaProvider
from app.infrastructure.llm.openrouter_provider import OpenRouterProvider

def get_llm_provider(model_id: str) -> LLMProvider:
    # If the model_id contains a slash it's a provider/model string → OpenRouter.
    # Only bare local model names (no slash) are routed to Ollama.
    if "/" in model_id:
        return OpenRouterProvider()
    return OllamaProvider()