import pytest
from app.services.rag_service import RAGService

@pytest.mark.asyncio
async def test_retrieve_context_stub():
    service = RAGService()
    context = await service.retrieve_context("test query")
    assert isinstance(context, list)
    assert len(context) == 0
