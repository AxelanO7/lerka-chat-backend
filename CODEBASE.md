# LERKA-CHAT-BACKEND — Python AI Chat Backend

FastAPI backend yang mengelola AI chat streaming dari local models (Ollama) dan cloud providers (OpenRouter).

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [LLM Providers](#llm-providers)
- [Architecture](#architecture)
- [Configuration](#configuration)
- [Development Setup](#development-setup)

---

## Project Overview

**Project Name:** LERKA-CHAT-BACKEND  
**Type:** Python REST API (FastAPI)  
**Purpose:** AI chat completion streaming backend  
**Status:** 🟢 Production Ready  
**Port:** 8000

### Features
- ✅ Local AI via Ollama (free tier - Gemma model)
- ✅ Cloud AI via OpenRouter (GPT-4o, Gemini, Claude, Llama)
- ✅ Server-Sent Events (SSE) streaming
- ✅ Token usage tracking
- ✅ Internal API security
- ✅ Containerized with Docker

---

## Tech Stack

| Category | Technology | Version |
|----------|-----------|---------|
| **Framework** | FastAPI | 0.110.0+ |
| **Server** | Uvicorn | 0.27.0+ |
| **Validation** | Pydantic | 2.6.0+ |
| **HTTP Client** | httpx | 0.27.0+ |
| **Config** | python-dotenv | 1.0.1+ |
| **Python** | Python | 3.11+ |

---

## Project Structure

```
lerka-chat-backend/
├── main.py                      # FastAPI app & CORS setup
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Container image
├── docker-compose.yml          # Local dev environment
├── .env.example                # Environment variables template
├── .env                        # Actual env (not in repo)
│
├── app/
│   ├── __init__.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py             # Dependency injection (auth)
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── chat.py         # Chat streaming endpoints
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Configuration management
│   │   ├── exceptions.py       # Custom exceptions
│   │   └── logging.py          # Structured logging
│   │
│   ├── domain/
│   │   ├── __init__.py
│   │   └── interfaces/
│   │       ├── __init__.py
│   │       └── llm_provider.py # Abstract LLM interface
│   │
│   ├── infrastructure/
│   │   ├── __init__.py
│   │   └── llm/
│   │       ├── __init__.py
│   │       ├── factory.py      # Provider selection factory
│   │       ├── ollama_provider.py      # Local Ollama
│   │       └── openrouter_provider.py  # Cloud OpenRouter
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── chat.py             # Pydantic models
│   │
│   └── services/
│       ├── __init__.py
│       └── chat_service.py     # Chat business logic
│
└── __pycache__                 # Python cache (gitignored)
```

---

## API Endpoints

### `POST /api/v1/chat/stream`

Stream chat completion responses token-by-token.

**Authentication:**
- Header: `X-Internal-Secret`
- Must match `INTERNAL_GATEWAY_SECRET` from .env
- Returns 403 Forbidden if invalid

**Request Body (Pydantic Model):**
```python
class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model_id: str  # e.g., "gemma:2b", "openai/gpt-4o-mini"
    temperature: float = 0.7  # 0.0-1.0
```

**Example Request:**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Explain clean architecture in Python."
    }
  ],
  "model_id": "openai/gpt-4o-mini",
  "temperature": 0.7
}
```

**Response:** Server-Sent Events (SSE)
```
data: Explanation
data:  of
data:  clean
data:  architecture
...
data: __USAGE__ {"prompt_tokens": 15, "completion_tokens": 42}
```

**Response Format:**
- Each line: `data: {token}`
- Token lines contain streaming text chunks
- Last line: `data: __USAGE__ {json}` with token counts
- HTTP Status: 200 OK

**Status Codes:**
- 200 OK (streaming)
- 400 Bad Request (invalid input)
- 403 Forbidden (auth failed)
- 500 Server Error

---

## LLM Providers

### Provider Factory Pattern

**File:** `app/infrastructure/llm/factory.py`

**Selection Logic:**
```python
if model_id == "gemma":
    return OllamaProvider()  # Local
else:
    return OpenRouterProvider()  # Cloud
```

**Available Models:**

| Model ID | Provider | Type | Cost | Tier |
|----------|----------|------|------|------|
| `gemma:2b` | Ollama | Local | Free | Free |
| `openai/gpt-4o-mini` | OpenRouter | Cloud | 💰 | Paid |
| `google/gemini-2.0-flash-001` | OpenRouter | Cloud | 💰 | Paid |
| `meta-llama/llama-3.1-8b-instruct` | OpenRouter | Cloud | 💰 | Paid |
| `anthropic/claude-3-haiku` | OpenRouter | Cloud | 💰 | Paid |

### OllamaProvider

**Purpose:** Run open-source models locally (privacy-focused)

**File:** `app/infrastructure/llm/ollama_provider.py`

**Configuration:**
- Base URL: `http://localhost:11434` (environment variable)
- Endpoint: `/api/chat`
- Model: Must be pulled via `ollama pull gemma:2b`

**Request Format:**
```json
{
  "model": "gemma:2b",
  "stream": true,
  "temperature": 0.7,
  "messages": [...]
}
```

**Response Parsing:**
- Stream format: `data: {"response":"token","done":false}`
- Token extraction: `response` field
- Done flag: `done: true` signals end
- Token counting: `prompt_eval_count` + `eval_count`

**Error Handling:**
- If Ollama unavailable: Returns error in stream
- Malformed responses: Logged and skipped
- Connection timeout: 30 seconds

**Integration Example:**
```python
async def stream():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_BASE_URL}/api/chat",
            json={...}
        ) as response:
            async for line in response.aiter_lines():
                token = parse_response(line)
                yield f"data: {token}\n\n"
```

### OpenRouterProvider

**Purpose:** Cloud-based LLM access (advanced models)

**File:** `app/infrastructure/llm/openrouter_provider.py`

**Configuration:**
- Base URL: `https://openrouter.ai/api/v1`
- API Key: `OPENROUTER_API_KEY` from .env
- Header: `Authorization: Bearer {key}`

**Request Format (OpenAI-compatible):**
```json
{
  "model": "openai/gpt-4o-mini",
  "temperature": 0.7,
  "stream": true,
  "messages": [...]
}
```

**Response Parsing:**
- SSE format: `data: {json_object}`
- Token extraction: `choices[0].delta.content`
- Finish detection: `finish_reason: "stop"`
- Token counting: `usage` field in final message

**Error Handling:**
- 400 Bad Request: Log and return error
  - Common: empty message from filtering
  - Solution: Skip empty messages before sending
- Rate limiting: 429 Too Many Requests (retryable)
- Invalid key: 401 Unauthorized

**Integration Example:**
```python
async def stream():
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    async with httpx.AsyncClient(headers=headers, timeout=300.0) as client:
        async with client.stream("POST", OPENROUTER_URL, json=payload) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    delta = parse_delta(line[6:])
                    if delta:
                        yield f"data: {delta['content']}\n\n"
```

### Abstract LLMProvider Interface

**File:** `app/domain/interfaces/llm_provider.py`

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def stream_completion(
        self,
        messages: List[ChatMessage],
        model_id: str,
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Yield tokens one-by-one from model completion."""
        pass
```

---

## Architecture

### Request Flow

```
Client Request
    ↓
FastAPI App (main.py)
    ↓ CORS Check
    ↓
Dependency: validate_internal_secret()
    ├─ Check X-Internal-Secret header
    ├─ Compare with INTERNAL_GATEWAY_SECRET
    └─ Raise 403 if invalid
    ↓
Route Handler: chat_endpoint()
    ├─ Validate request (Pydantic)
    ├─ Call ChatService.stream_completion()
    └─ Return SSE StreamingResponse
    ↓
ChatService
    ├─ Get LLMProvider via factory
    ├─ Call provider.stream_completion()
    └─ Yield tokens
    ↓
LLMProvider (Ollama or OpenRouter)
    ├─ Make HTTP request to service
    ├─ Parse streaming response
    └─ Yield tokens
    ↓
SSE Stream to Client
    └─ Token by token
```

### Error Handling

**Global Exception Handler** (`app/core/exceptions.py`):
```python
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )
```

### Logging

**Structured Logging** (`app/core/logging.py`):
- JSON format for production
- INFO level by default
- ERROR level for failures
- Context: request ID, model, user

---

## Configuration

**File:** `app/core/config.py`

```python
class Settings(BaseSettings):
    # API
    PROJECT_NAME: str = "Lerka AI Worker"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # LLM Providers
    OPENROUTER_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # Security
    INTERNAL_GATEWAY_SECRET: str = ""
    
    class Config:
        env_file = ".env"
```

**Environment Variables (.env):**
```bash
# API
PROJECT_NAME=Lerka AI Worker
API_V1_STR=/api/v1
VERSION=1.0.0
ENVIRONMENT=development

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8081

# LLM
OPENROUTER_API_KEY=your-api-key
OLLAMA_BASE_URL=http://localhost:11434

# Security
INTERNAL_GATEWAY_SECRET=internal-secret-key
```

---

## Development Setup

### Prerequisites
- Python 3.11+
- pip or poetry
- (Optional) Ollama for local models
- Docker (optional)

### Using Docker Compose

```bash
# Start Python backend
docker-compose up --build

# Runs on:
# - http://localhost:8000
# - API docs: http://localhost:8000/docs
```

### Local Setup

**1. Create Virtual Environment:**
```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
```

**2. Install Dependencies:**
```bash
pip install -r requirements.txt
```

**3. Create .env File:**
```bash
cp .env.example .env
# Update with your keys:
# - OPENROUTER_API_KEY
# - INTERNAL_GATEWAY_SECRET
```

**4. (Optional) Setup Ollama:**
```bash
# Download Ollama from https://ollama.ai
# Pull Gemma model
ollama pull gemma:2b
```

**5. Run Server:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**6. Access API:**
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Testing

### Test Streaming Endpoint (cURL)

```bash
curl -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "X-Internal-Secret: internal-secret-key" \
  -d '{
    "messages": [
      {"role": "system", "content": "You are helpful."},
      {"role": "user", "content": "Say hello"}
    ],
    "model_id": "gemma:2b",
    "temperature": 0.7
  }'
```

### Test with Python

```python
import httpx
import json

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "http://localhost:8000/api/v1/chat/stream",
        headers={"X-Internal-Secret": "secret"},
        json={
            "messages": [{"role": "user", "content": "Hello"}],
            "model_id": "gemma:2b",
            "temperature": 0.7
        }
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                print(line[6:])
```

---

## Troubleshooting

**Issue:** 403 Unauthorized  
**Solution:** Check X-Internal-Secret header matches INTERNAL_GATEWAY_SECRET

**Issue:** 500 Error from Ollama  
**Solution:** Ensure Ollama is running and model is pulled (`ollama pull gemma:2b`)

**Issue:** OpenRouter rate limiting  
**Solution:** Add retry logic or wait before next request

**Issue:** Slow streaming  
**Solution:** Check network latency, increase timeout, use faster model

**Issue:** Memory errors  
**Solution:** For Ollama, reduce model size or increase system RAM

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `main.py` | FastAPI app initialization & CORS |
| `app/api/routes/chat.py` | Chat streaming endpoint |
| `app/api/deps.py` | Authentication dependency |
| `app/core/config.py` | Configuration management |
| `app/infrastructure/llm/factory.py` | Provider selection |
| `app/infrastructure/llm/ollama_provider.py` | Local LLM |
| `app/infrastructure/llm/openrouter_provider.py` | Cloud LLM |
| `app/schemas/chat.py` | Request/response models |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container image |
| `.env.example` | Environment template |

---

**Last Updated:** June 2026  
**Status:** 🟢 Production Ready  
**Maintained By:** Engineering Team
