from app.infrastructure.llm.factory import get_llm_provider
from app.services.chat_service import ChatService
from app.services.rag_service import RAGService

def get_rag_service() -> RAGService:
    return RAGService()

def get_chat_service() -> ChatService:
    provider = get_llm_provider()
    rag_service = get_rag_service()
    return ChatService(llm_provider=provider, rag_service=rag_service) 