# central settings loader
from dotenv import load_dotenv
load_dotenv()

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App settings
    app_name: str = "AI Support Agent"
    app_env: str = Field(default="development", env="APP_ENV")
    debug: bool = Field(default=False, env="DEBUG")
    api_key: Optional[str] = Field(default=None, env="API_KEY")
    allowed_origins: List[str] = Field(default=[], env="ALLOWED_ORIGINS")

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
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

    # Observability
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    otlp_endpoint: Optional[str] = Field(default=None, env="OTLP_ENDPOINT")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    def validate_production(self) -> None:
        """
        Validates that production settings are safe.
        Raises ValueError if unsafe defaults are detected in production mode.
        Called during application startup.
        """
        if not self.is_production:
            return

        errors = []

        if self.debug:
            errors.append("DEBUG mode cannot be enabled in production (debug=True)")

        if not self.allowed_origins or "*" in self.allowed_origins:
            errors.append("ALLOWED_ORIGINS must be explicitly configured in production (not '*', not empty)")

        if not self.rate_limit_enabled:
            errors.append("RATE_LIMIT_ENABLED must be True in production")

        if self.api_key is None:
            errors.append("API_KEY must be set for production deployments")

        if self.is_production and not (self.openai_api_key or self.anthropic_api_key):
            errors.append("At least one LLM provider API key must be configured in production")

        if errors:
            raise ValueError(
                f"Production configuration validation failed:\n" + "\n".join(f"  - {e}" for e in errors)
            )

    def validate_llm_config(self) -> None:
        """
        Validates LLM configuration.
        Ensures at least one provider is configured.
        """
        if not self.openai_api_key and not self.anthropic_api_key:
            raise ValueError("At least one LLM provider API key must be configured")

        if self.default_llm_provider not in ["openai", "anthropic"]:
            raise ValueError(f"Invalid default_llm_provider: {self.default_llm_provider}")

        if self.fallback_provider and self.fallback_provider not in ["openai", "anthropic"]:
            raise ValueError(f"Invalid fallback_provider: {self.fallback_provider}")


# Global settings instance
settings = Settings()
