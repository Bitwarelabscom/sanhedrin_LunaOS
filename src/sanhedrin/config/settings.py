"""
Configuration settings using Pydantic Settings.

Loads from environment variables and .env files.
"""

from __future__ import annotations

from typing import Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServerSettings(BaseSettings):
    """Server configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SANHEDRIN_",
        env_file=".env",
        extra="ignore",
    )

    host: str = Field(default="127.0.0.1", description="Server host (default: localhost for security)")
    port: int = Field(default=8000, description="Server port", ge=1, le=65535)
    base_url: str | None = Field(default=None, description="Public base URL")
    reload: bool = Field(default=False, description="Enable auto-reload")
    workers: int = Field(default=1, description="Number of worker processes", ge=1)
    shutdown_grace_period: int = Field(default=5, description="Graceful shutdown wait time", ge=0)


class SecuritySettings(BaseSettings):
    """Security configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SANHEDRIN_",
        env_file=".env",
        extra="ignore",
    )

    auth_enabled: bool = Field(default=False, description="Enable API key authentication")
    api_keys: str = Field(default="", description="Comma-separated list of valid API keys")
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=60, description="Requests per minute per client", ge=1)
    rate_limit_per_hour: int = Field(default=1000, description="Requests per hour per client", ge=1)
    rate_limit_burst: int = Field(default=10, description="Burst size for rate limiting", ge=1)
    cors_origins: str = Field(default="", description="Comma-separated CORS origins (empty = disabled)")

    @property
    def api_keys_list(self) -> list[str]:
        """Get API keys as list."""
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


class AdapterSettings(BaseSettings):
    """Adapter configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SANHEDRIN_",
        env_file=".env",
        extra="ignore",
    )

    adapter: str = Field(default="claude-code", description="Default adapter")
    timeout: float = Field(default=120.0, description="Execution timeout in seconds", gt=0)
    max_retries: int = Field(default=3, description="Max retry attempts", ge=0)
    max_prompt_length: int = Field(default=100000, description="Maximum prompt length", gt=0)
    max_context_messages: int = Field(default=100, description="Maximum messages in context", gt=0)


class TaskSettings(BaseSettings):
    """Task management configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SANHEDRIN_",
        env_file=".env",
        extra="ignore",
    )

    cleanup_enabled: bool = Field(default=True, description="Enable automatic task cleanup")
    cleanup_interval: int = Field(default=300, description="Cleanup interval in seconds", ge=60)
    task_max_age: int = Field(default=3600, description="Max task age in seconds before cleanup", ge=60)
    max_concurrent_tasks: int = Field(default=100, description="Maximum concurrent tasks", ge=1)


class OllamaSettings(BaseSettings):
    """Ollama-specific settings."""

    model_config = SettingsConfigDict(
        env_prefix="OLLAMA_",
        env_file=".env",
        extra="ignore",
    )

    host: str = Field(
        default="http://localhost:11434",
        description="Ollama server URL",
    )
    model: str = Field(default="llama3.2", description="Default model")


class CacheSettings(BaseSettings):
    """Cache configuration."""

    model_config = SettingsConfigDict(
        env_prefix="SANHEDRIN_CACHE_",
        env_file=".env",
        extra="ignore",
    )

    enabled: bool = Field(default=True, description="Enable caching")
    max_size: int = Field(default=1000, description="Maximum cache entries", ge=1)
    default_ttl: int = Field(default=300, description="Default TTL in seconds", ge=1)


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="SANHEDRIN_",
        env_file=".env",
        extra="ignore",
    )

    # Environment
    env: str = Field(default="production", description="Environment (production, development)")

    # Nested settings
    server: ServerSettings = Field(default_factory=ServerSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    adapter: AdapterSettings = Field(default_factory=AdapterSettings)
    task: TaskSettings = Field(default_factory=TaskSettings)
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format string",
    )
    log_json: bool = Field(default=False, description="Use JSON log format")

    # Provider info
    provider_name: str = Field(default="Sanhedrin", description="Provider name")
    provider_url: str = Field(
        default="https://github.com/sanhedrin",
        description="Provider URL",
    )

    @field_validator("env")
    @classmethod
    def validate_env(cls, v: str) -> str:
        """Validate environment value."""
        valid = {"production", "development", "testing"}
        if v.lower() not in valid:
            raise ValueError(f"env must be one of: {valid}")
        return v.lower()

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.env == "development"

    def get_base_url(self) -> str:
        """Get effective base URL."""
        if self.server.base_url:
            return self.server.base_url
        return f"http://{self.server.host}:{self.server.port}"


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """Force reload settings."""
    global _settings
    _settings = Settings()
    return _settings
