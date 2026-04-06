# central settings loader
from dotenv import load_dotenv
load_dotenv()

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    app_name: str = "AI Support Agent"
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=True, env="DEBUG")
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    allowed_origins: List[str] = Field(default=["*"], env="ALLOWED_ORIGINS")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=False, env="RATE_LIMIT_ENABLED")
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")

    # LLM settings
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")
    default_model: str = Field(default="gpt-4o-mini", env="DEFAULT_MODEL")
    fallback_model: str = Field(default="claude-3-haiku", env="FALLBACK_MODEL")
    default_llm_provider: str = Field(default="openai", env="DEFAULT_LLM_PROVIDER")
    fallback_provider: Optional[str] = Field(default="anthropic", env="FALLBACK_PROVIDER")
    llm_routing_strategy: str = Field(default="cost", env="LLM_ROUTING_STRATEGY")

    # Memory settings
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    enable_rag: bool = Field(default=True, env="ENABLE_RAG")

    # Knowledge base settings
    rag_vector_store_path: str = Field(default="./vector_store", env="RAG_VECTOR_STORE_PATH")
    rag_chunk_size: int = Field(default=1000, env="RAG_CHUNK_SIZE")
    rag_chunk_overlap: int = Field(default=200, env="RAG_CHUNK_OVERLAP")
    rag_max_results: int = Field(default=5, env="RAG_MAX_RESULTS")
    rag_score_threshold: float = Field(default=0.7, env="RAG_SCORE_THRESHOLD")

    # Database
    database_url: Optional[str] = Field(default=None, env="DATABASE_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


# Global settings instance
settings = Settings()
