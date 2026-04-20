# AI Chat Backend

A robust, production-ready backend built with FastAPI, designed to power an AI chat system using both local models (Ollama) and cloud providers (OpenRouter). 

## Features
- **Local & Cloud AI** — Supports Ollama for local execution and OpenRouter for cloud-based inference.
- **Streaming Responses** — Server-Sent Events (SSE) provide a fast, token-by-token visual feedback loop for chat completions.
- **Secure Internal API** — Protected by an internal gateway secret to ensure requests only come from the API Gateway.
- **Fully Containerized** — Seamless deployment using Docker Compose.

## Architecture

- **`api/`**: Controllers and dependency injection (`deps.py`).
- **`core/`**: Configuration, settings, global exceptions, and structured logging.
- **`domain/`**: Key business entities and interfaces (`LLMProvider`).
- **`infrastructure/`**: Concrete integrations (`OllamaProvider`, `OpenRouterProvider`).
- **`schemas/`**: Pydantic validation models.
- **`services/`**: The application business logic (`ChatService`).

## Getting Started

### Setup Environment
```bash
cp .env.example .env
```
Update the `.env` file with your `OPENROUTER_API_KEY` and ensure `INTERNAL_GATEWAY_SECRET` matches the one in your API Gateway.

### 1. Using Docker Compose (Recommended)
This is the easiest way to run the stack.
```bash
docker compose up --build -d
```

### 2. Running Locally (Without Docker)

**Install Dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

**Run Server:**
```bash
uvicorn main:app --reload
```

## Endpoints

### `POST /api/v1/chat/stream`
Streams a chat completion chunk-by-chunk using Server-Sent Events (SSE).

**Headers Required:**
- `X-Internal-Secret`: Must match the `INTERNAL_GATEWAY_SECRET` from your `.env`

**Example Payload:**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Explain clean architecture."
    }
  ],
  "model_id": "llama3.2:3b",
  "temperature": 0.7
}
```
