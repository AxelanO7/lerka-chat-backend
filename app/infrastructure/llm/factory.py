from app.domain.interfaces.llm_provider import LLMProvider
from app.infrastructure.llm.ollama_provider import OllamaProvider
from app.infrastructure.llm.openrouter_provider import OpenRouterProvider

def get_llm_provider(model_id: str) -> LLMProvider:
    # Route local models to Ollama (local)
    local_models = ["gemma", "gemma4", "llama3.1:8b", "llama"]
    if model_id in local_models or "/" not in model_id:
        return OllamaProvider()
    
    # Models with provider prefixes go to OpenRouter (cloud)
    return OpenRouterProvider()