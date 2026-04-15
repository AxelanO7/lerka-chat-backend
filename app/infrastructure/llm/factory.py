from app.domain.interfaces.llm_provider import LLMProvider
from app.infrastructure.llm.ollama_provider import OllamaProvider
from app.infrastructure.llm.openrouter_provider import OpenRouterProvider

def get_llm_provider(model_id: str) -> LLMProvider:
    # Route local/ollama models to OllamaProvider, others to OpenRouter
    if model_id.startswith(('llama', 'mistral', 'gemma', 'phi', 'qwen', 'codellama')):
        return OllamaProvider()
    return OpenRouterProvider()