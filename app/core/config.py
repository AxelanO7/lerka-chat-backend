from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Dict, Any

class Settings(BaseSettings):
    PROJECT_NAME: str = "Lerka AI Worker"
    API_V1_STR: str = "/api/v1"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    OPENROUTER_API_KEY: str = ""
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    INTERNAL_GATEWAY_SECRET: str = "your-internal-gateway-secret-here"
    
    # DEV_MODE: refuse to boot if DEV_MODE=true
    DEV_MODE: bool = False
    
    # Postgres configuration
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "lerka"
    
    # Redis configuration (logical DB 0 for control, DB 1 for cache to protect control keys)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB_CONTROL: int = 0
    REDIS_DB_CACHE: int = 1
    
    # Caching and Embeddings
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.93
    MODEL_SET_VERSION: str = "v1"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en"
    
    # Cost controls
    APP_DAILY_SPEND_CAP_USD: float = 25.0
    
    # Models
    FREE_FORM_LIVE_MODEL: str = "openai/gpt-oss-20b"
    COMPARE_LIVE_MODELS: List[str] = ["openai/gpt-oss-20b", "google/gemma-4-26b-a4b-it"]
    JUDGE_MODEL: str = "google/gemma-4-26b-a4b-it"
    
    SHOWCASE_FREE_MODELS: List[str] = [
        "openai/gpt-oss-20b:free",
        "openai/gpt-oss-120b:free",
        "google/gemma-4-31b-it:free",
        "google/gemma-4-26b-a4b-it:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "nvidia/nemotron-nano-9b-v2:free",
        "poolside/laguna-m.1:free"
    ]
    
    # Showcases
    SHOWCASES: List[Dict[str, str]] = [
        {
            "id": "reasoning-puzzle",
            "title": "Reasoning Puzzle",
            "prompt": "If a tree falls in a forest and no one is around to hear it, does it make a sound? Answer in one short paragraph from a philosophical and a scientific perspective."
        },
        {
            "id": "creative-writing",
            "title": "Creative Writing",
            "prompt": "Write a haiku about the transition from autumn to winter, focusing on the wind."
        },
        {
            "id": "indonesian-slang",
            "title": "Indonesian Slang Translation",
            "prompt": "Translate 'Kamu nanya? Biar aku kasih tau ya' into formal English and explain the cultural context of the meme."
        }
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

settings = Settings()