"""Application configuration using Pydantic Settings."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    app_name: str = "Tool Hub API"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./tool_hub.db"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10

    # Security
    secret_key: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # CORS
    cors_origins: str = "http://localhost:5173,http://localhost:5174"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # "json" for production, "text" for development

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    server_workers: int = 1
    scheduler_enabled: bool = True  # Set False for non-primary workers in horizontal scaling

    # LLM Providers
    openai_api_key: str = ""
    openai_base_url: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    gemini_api_key: str = ""
    default_llm_model: str = "gpt-4o-mini"
    llm_timeout: float = 120.0
    llm_max_tokens: int = 4096
    llm_temperature: float = 0.7

    # Embedding Provider
    embedding_provider: str = "openai"  # "openai", "ollama", "hash" (fallback)
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_sqlite(self) -> bool:
        return "sqlite" in self.database_url

    @property
    def available_providers(self) -> list[str]:
        providers = []
        if self.openai_api_key:
            providers.append("openai")
        if self.anthropic_api_key:
            providers.append("anthropic")
        if self.ollama_base_url:
            providers.append("ollama")
        if self.gemini_api_key:
            providers.append("google")
        return providers

    @property
    def has_llm_keys(self) -> bool:
        return bool(self.openai_api_key or self.anthropic_api_key or self.gemini_api_key)

    def validate_production_secrets(self) -> None:
        """Raise if production is using placeholder secrets."""
        if not self.is_production:
            return
        weak = {"", "change-me-in-production"}
        if self.secret_key in weak:
            raise ValueError("SECRET_KEY must be set to a strong value in production")
        if self.jwt_secret in weak:
            raise ValueError("JWT_SECRET must be set to a strong value in production")

    model_config = {"env_prefix": "", "case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
