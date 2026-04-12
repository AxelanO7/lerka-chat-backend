from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Chat System API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    ENVIRONMENT: str = "development"
    
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://host.docker.internal:11434"
    OLLAMA_TIMEOUT: float = 300.0
    DEFAULT_MODEL: str = "llama3.2:3b"
    ALLOWED_ORIGINS: list[str] = ["*"]

    # Budget Limits defaults
    BUDGET_LLAMA_3_2: int = 100000
    BUDGET_LLAMA_2: int = 100000
    BUDGET_GEMMA4: int = 100000
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

settings = Settings()