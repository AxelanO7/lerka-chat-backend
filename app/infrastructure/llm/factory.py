from app.domain.interfaces.llm_provider import LLMProvider
from app.infrastructure.llm.ollama_provider import OllamaProvider

def get_llm_provider() -> LLMProvider:
    return OllamaProvider()