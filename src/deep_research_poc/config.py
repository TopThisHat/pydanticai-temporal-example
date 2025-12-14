"""Configuration management using Pydantic settings.

This module provides type-safe configuration loaded from environment variables.
Settings are validated at startup and cached for performance.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables or .env file.
    Environment variables use the same names (case-insensitive).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(
        ...,
        description="OpenAI API key for AI research capabilities",
    )
    openai_model: str = Field(
        default="gpt-5",
        description="OpenAI model to use (e.g., gpt-4o, gpt-4-turbo)",
    )
    openai_max_tokens: int = Field(
        default=4096,
        ge=100,
        le=128000,
        description="Maximum tokens for AI responses",
    )
    openai_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Temperature for AI responses (0=deterministic, 2=creative)",
    )

    # Temporal Configuration
    temporal_address: str = Field(
        default="localhost:7233",
        description="Temporal server address",
    )
    temporal_namespace: str = Field(
        default="default",
        description="Temporal namespace",
    )
    temporal_task_queue: str = Field(
        default="deep-research-queue",
        description="Temporal task queue name for research workflows",
    )

    # Research Configuration
    max_research_iterations: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Default maximum research iterations",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.
    
    Settings are loaded once and cached for the lifetime of the application.
    Use this function instead of instantiating Settings directly.
    
    Returns:
        Cached Settings instance
    """
    return Settings()  # type: ignore[call-arg]
