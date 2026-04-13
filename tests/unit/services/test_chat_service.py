import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.chat_service import ChatService
from app.domain.entities.message import Message
from app.schemas.chat import ChatRequest
from app.core.config import settings

@pytest.fixture
def chat_service(mock_llm_provider, mock_rag_service, mock_budget_service):
    return ChatService(
        llm_provider=mock_llm_provider,
        rag_service=mock_rag_service,
        budget_service=mock_budget_service
    )

@pytest.mark.asyncio
async def test_prepare_messages_no_rag(chat_service, sample_messages):
    prepared = await chat_service._prepare_messages(sample_messages, use_rag=False)
    assert prepared == sample_messages

@pytest.mark.asyncio
async def test_prepare_messages_with_rag(chat_service, sample_messages, mock_rag_service):
    mock_rag_service.retrieve_context.return_value = ["Fact A", "Fact B"]
    
    prepared = await chat_service._prepare_messages(sample_messages, use_rag=True)
    
    assert len(prepared) == len(sample_messages)
    last_msg = prepared[-1]
    assert "Fact A" in last_msg.content
    assert "Fact B" in last_msg.content
    assert "Tell me about AI" in last_msg.content
    mock_rag_service.retrieve_context.assert_called_once_with("Tell me about AI")

@pytest.mark.asyncio
async def test_process_chat_stream_insufficient_budget(chat_service, mock_budget_service):
    mock_budget_service.get_budget.return_value = 0
    request = ChatRequest(
        messages=[Message(role="user", content="hello")],
        model="llama3.2:3b",
        use_rag=False
    )
    
    with pytest.raises(ValueError, match="Insufficient budget"):
        async for _ in chat_service.process_chat_stream(request):
            pass

@pytest.mark.asyncio
async def test_process_chat_stream_success(chat_service, mock_llm_provider, mock_budget_service):
    mock_budget_service.get_budget.return_value = 1000
    
    # Mock the generator
    async def mock_gen(*args, **kwargs):
        yield "Hello"
        yield " world"
        if "on_usage_callback" in kwargs:
            kwargs["on_usage_callback"](10, 20)

    mock_llm_provider.generate_stream = mock_gen
    
    request = ChatRequest(
        messages=[Message(role="user", content="hi")],
        model="llama3.2:3b",
        use_rag=False
    )
    
    chunks = []
    async for chunk in chat_service.process_chat_stream(request):
        chunks.append(chunk)
        
    assert "".join(chunks) == "Hello world"
    mock_budget_service.deduct_budget.assert_called_once_with("llama3.2:3b", 30)

@pytest.mark.asyncio
async def test_process_chat_stream_default_model(chat_service, mock_llm_provider, mock_budget_service):
    # Test that "string" model name defaults to settings.DEFAULT_MODEL
    mock_llm_provider.generate_stream = AsyncMock() # Just to avoid error
    
    request = ChatRequest(
        messages=[Message(role="user", content="hi")],
        model="string", # Swagger default
        use_rag=False
    )
    
    # We just want to check if it calls get_budget with default model
    try:
        async for _ in chat_service.process_chat_stream(request):
            pass
    except Exception:
        pass
        
    mock_budget_service.get_budget.assert_called_with(settings.DEFAULT_MODEL)
