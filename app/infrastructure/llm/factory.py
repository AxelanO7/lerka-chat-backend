from app.domain.interfaces.llm_provider import LLMProvider
from app.infrastructure.llm.ollama_provider import OllamaProvider
from app.infrastructure.llm.openrouter_provider import OpenRouterProvider

FREE_TIER_MODELS = {
    "openai/gpt-oss-20b",
    "google/gemma-3-4b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "deepseek/deepseek-v3-base:free",
}

LOCAL_OLLAMA_MODELS = {
    "gemma", "gemma3", "gemma3:4b",
    "llama", "llama3", "llama3.1", "llama3.2", "llama3.2:3b", "llama3.2:latest",
    "qwen", "qwen3", "qwen3:8b", "qwen2.5-coder:14b",
    "deepseek-r1", "deepseek-r1:8b",
}

def get_llm_provider(model_id: str) -> LLMProvider:
    """Route model to provider based on model ID format.
    - Ollama: models without "/" or matching LOCAL_OLLAMA_MODELS
    - OpenRouter: models with vendor prefix (e.g., deepseek/, anthropic/)
    """
    # Check if it's a known local model
    if model_id in LOCAL_OLLAMA_MODELS:
        return OllamaProvider()

    # Models without "/" are assumed to be local (Ollama format: "name:tag")
    if "/" not in model_id:
        return OllamaProvider()

    # Models with provider prefixes go to OpenRouter (cloud)
    return OpenRouterProvider()