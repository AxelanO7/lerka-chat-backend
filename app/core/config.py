from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Chat System API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    
    LLM_PROVIDER: str = "openrouter"
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_TIMEOUT: float = 300.0
    OPENROUTER_API_KEY: str = ""
    DEFAULT_MODEL: str = "llama3.2:3b"
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Budget Limits defaults
    BUDGET_LLAMA_3_2: int = 100000
    BUDGET_LLAMA_2: int = 100000
    BUDGET_GEMMA4: int = 100000
    
    # OpenRouter Models Budgets
    BUDGET_OR_LLAMA_3_1_8B: int = 10000
    BUDGET_OR_CLAUDE_3_HAIKU: int = 5000
    BUDGET_OR_GPT_4O_MINI: int = 10000
    
    # MongoDB Settings
    MONGODB_URL: str = "mongodb://root:example@localhost:27017/"
    MONGODB_DATABASE: str = "lerka_chat"
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

settings = Settings()