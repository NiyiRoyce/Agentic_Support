# central settings loader
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings
from typing import Optional, List

from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
    )

    # App settings
    app_name: str = "AI Support Agent"
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    api_key: Optional[str] = Field(default=None)
    allowed_origins: List[str] = Field(default=[])

    # Rate limiting
    rate_limit_enabled: bool = Field(default=True)
    rate_limit_requests_per_minute: int = Field(default=60)

    # LLM settings
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    default_model: str = Field(default="gpt-4o-mini")
    fallback_model: str = Field(default="claude-3-haiku")
    default_llm_provider: str = Field(default="openai")
    fallback_provider: Optional[str] = Field(default="anthropic")
    llm_routing_strategy: str = Field(default="cost")

    # Memory settings
    redis_url: Optional[str] = Field(default=None)
    enable_rag: bool = Field(default=True)

    # Knowledge base settings
    rag_vector_store_path: str = Field(default="./vector_store")
    rag_chunk_size: int = Field(default=1000)
    rag_chunk_overlap: int = Field(default=200)
    rag_max_results: int = Field(default=5)
    rag_score_threshold: float = Field(default=0.7)

    # Observability
    log_level: str = Field(default="INFO")
    otlp_endpoint: Optional[str] = Field(default=None)

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
            errors.append(
                "ALLOWED_ORIGINS must be explicitly configured in production (not '*', not empty)"
            )

        if not self.rate_limit_enabled:
            errors.append("RATE_LIMIT_ENABLED must be True in production")

        if self.api_key is None:
            errors.append("API_KEY must be set for production deployments")

        if self.is_production and not (self.openai_api_key or self.anthropic_api_key):
            errors.append(
                "At least one LLM provider API key must be configured in production"
            )

        if errors:
            raise ValueError(
                "Production configuration validation failed:\n"
                + "\n".join(f"  - {e}" for e in errors)
            )

    def validate_llm_config(self) -> None:
        """
        Validates LLM configuration.
        Ensures at least one provider is configured.
        """
        if not self.openai_api_key and not self.anthropic_api_key:
            raise ValueError("At least one LLM provider API key must be configured")

        if self.default_llm_provider not in ["openai", "anthropic"]:
            raise ValueError(
                f"Invalid default_llm_provider: {self.default_llm_provider}"
            )

        if self.fallback_provider and self.fallback_provider not in [
            "openai",
            "anthropic",
        ]:
            raise ValueError(f"Invalid fallback_provider: {self.fallback_provider}")


# Global settings instance
settings = Settings()
