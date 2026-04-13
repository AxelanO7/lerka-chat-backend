from app.domain.interfaces.llm_provider import LLMProvider
from app.infrastructure.llm.ollama_provider import OllamaProvider
from app.infrastructure.llm.openrouter_provider import OpenRouterProvider
from app.core.config import settings

def get_llm_provider() -> LLMProvider:
    if settings.LLM_PROVIDER.lower() == "openrouter":
        return OpenRouterProvider()
    return OllamaProvider()