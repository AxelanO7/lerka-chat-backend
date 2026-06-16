from app.domain.interfaces.llm_provider import LLMProvider
from app.infrastructure.llm.ollama_provider import OllamaProvider
from app.infrastructure.llm.openrouter_provider import OpenRouterProvider

FREE_TIER_MODELS = {
    "openai/gpt-oss-20b",
    "google/gemma-3-4b-it:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "deepseek/deepseek-v3-base:free",
}

LOCAL_OLLAMA_MODELS = {"gemma", "gemma4", "llama", "llama3.1:8b"}

def get_llm_provider(model_id: str) -> LLMProvider:
    if model_id in LOCAL_OLLAMA_MODELS or "/" not in model_id:
        return OllamaProvider()
    
    # Models with provider prefixes go to OpenRouter (cloud)
    return OpenRouterProvider()