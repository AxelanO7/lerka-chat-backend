import pytest
from unittest.mock import AsyncMock, MagicMock
from app.domain.entities.message import Message

@pytest.fixture
def mock_llm_provider():
    return MagicMock()

@pytest.fixture
def mock_rag_service():
    service = MagicMock()
    service.retrieve_context = AsyncMock(return_value=[])
    return service

@pytest.fixture
def mock_budget_service():
    service = MagicMock()
    service.get_budget.return_value = 1000
    service.deduct_budget = MagicMock()
    return service

@pytest.fixture
def sample_messages():
    return [
        Message(role="user", content="Hello"),
        Message(role="assistant", content="Hi there!"),
        Message(role="user", content="Tell me about AI")
    ]
