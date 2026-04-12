from app.infrastructure.llm.factory import get_llm_provider
from app.services.chat_service import ChatService
from app.services.rag_service import RAGService
from app.services.budget_service import TokenBudgetService

def get_rag_service() -> RAGService:
    return RAGService()

# Singleton instance string state for the lifetime of the application
_budget_service = TokenBudgetService()

def get_budget_service() -> TokenBudgetService:
    return _budget_service

def get_chat_service() -> ChatService:
    provider = get_llm_provider()
    rag_service = get_rag_service()
    return ChatService(llm_provider=provider, rag_service=rag_service, budget_service=_budget_service) 