from app.domain.interfaces.llm_provider import LLMProvider
from app.infrastructure.llm.ollama_provider import OllamaProvider
from app.infrastructure.llm.openrouter_provider import OpenRouterProvider

def get_llm_provider(model_id: str) -> LLMProvider:
    # Explicitly route 'gemma' to Ollama (local)
    if model_id == "gemma":
        return OllamaProvider()
    
    # Everything else goes to OpenRouter (cloud)
    return OpenRouterProvider()