import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.infrastructure.llm.ollama_provider import OllamaProvider
from app.domain.entities.message import Message

@pytest.fixture
def ollama_provider():
    return OllamaProvider()

@pytest.mark.asyncio
async def test_generate_non_streaming(ollama_provider, mocker):
    # Mock httpx.AsyncClient and its context manager
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "Hello from Ollama"},
        "done": True,
        "prompt_eval_count": 10,
        "eval_count": 20
    }
    mock_response.raise_for_status = MagicMock()
    
    mock_client.post = AsyncMock(return_value=mock_response)
    mocker.patch("httpx.AsyncClient", return_value=mock_client)
    
    usage_called = False
    def usage_callback(p, e):
        nonlocal usage_called
        usage_called = True
        assert p == 10
        assert e == 20

    messages = [Message(role="user", content="Hi")]
    result = await ollama_provider.generate(
        messages=messages,
        model="llama3.2:3b",
        temperature=0.8,
        on_usage_callback=usage_callback
    )
    
    assert result == "Hello from Ollama"
    assert usage_called is True
    
    call_args = mock_client.post.call_args
    payload = call_args[1]["json"]
    assert payload["model"] == "llama3.2:3b"

@pytest.mark.asyncio
async def test_generate_stream(ollama_provider, mocker):
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mock_response = MagicMock()
    
    async def mock_aiter_lines():
        lines = [
            json.dumps({"message": {"content": "Hello"}, "done": False}),
            json.dumps({"message": {"content": " world"}, "done": True, "prompt_eval_count": 5, "eval_count": 5})
        ]
        for line in lines:
            yield line

    mock_response.aiter_lines = mock_aiter_lines
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()
    
    # Mock client.stream context manager
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=None)
    
    mock_client.stream.return_value = mock_stream_ctx
    mocker.patch("httpx.AsyncClient", return_value=mock_client)
    
    usage_data = {}
    def usage_callback(p, e):
        usage_data["p"] = p
        usage_data["e"] = e

    messages = [Message(role="user", content="Hi")]
    chunks = []
    async for chunk in ollama_provider.generate_stream(
        messages=messages,
        model="llama3.2:3b",
        temperature=0.5,
        budget_limit=100,
        on_usage_callback=usage_callback
    ):
        chunks.append(chunk)

    assert "".join(chunks) == "Hello world"
    assert usage_data == {"p": 5, "e": 5}

