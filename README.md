# AI Chat Backend (Ollama)

A robust, production-ready backend built with FastAPI, designed to power a fully local AI chat system using Ollama. It follows Clean Architecture principles allowing easy swapping of LLM and Vector Store dependencies.

## Features
- **Local AI** — Zero third-party dependencies, relies strictly on Ollama running on your machine.
- **Pre-baked LLM** — The `docker-compose` orchestration preloads the `llama3` model securely inside the image layers.
- **Streaming Responses** — Server-Sent Events (SSE) provide a fast, token-by-token visual feedback loop for chat completions.
- **RAG-Ready** — The service structure is completely decoupled allowing drops-in for FAISS, ChromaDB, or similar pipelines without disturbing the business logic (`rag_service.py`).
- **Fully Containerized** — Seamless networking between the API container and the Ollama container via Docker Compose.

## Architecture

- **`api/`**: Controllers and dependency injection (`deps.py`).
- **`core/`**: Configuration, settings, global exceptions, and structured logging.
- **`domain/`**: Key business entities and interfaces (`LLMProvider`, `VectorStore`, `EmbeddingProvider`).
- **`infrastructure/`**: Concrete integrations (e.g., `OllamaProvider`, network clients).
- **`schemas/`**: Pydantic validation models.
- **`services/`**: The true application business logic (`ChatService`, `RAGService`).

## Getting Started

### 1. Using Docker Compose (Recommended)
This is the easiest way to run the stack. The backend connects seamlessly to an internal Ollama container.

**Build and Start:**
```bash
docker compose up --build -d
```
> **Note**: On the initial build, Docker will download the `llama3` model and bake it into the Ollama image cache automatically. This might take a few minutes depending on your internet connection.

### 2. Running Locally (Without Docker)

**Start Ollama locally:**
Ensure Ollama is running on your machine on port `11434` and the model is pulled:
```bash
ollama serve
ollama pull llama3
```

**Setup Environment:**
```bash
cp .env.example .env
```
*(Ensure `.env` maps `LLM_PROVIDER=ollama` and `OLLAMA_BASE_URL=http://localhost:11434`)*

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

### `POST /api/chat`
Streams a chat completion chunk-by-chunk using Server-Sent Events (SSE).

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
  "model": "llama3",
  "temperature": 0.7,
  "use_rag": false
}
```
