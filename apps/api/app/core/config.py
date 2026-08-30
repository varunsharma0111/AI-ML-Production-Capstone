"""Typed, environment-backed application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or an ignored .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_name: str = "AI/ML Production Capstone API"
    log_level: str = "INFO"
    database_url: str = Field(default="postgresql+asyncpg://localhost/capstone")
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=20)
    oidc_issuer: HttpUrl | str = Field(default="https://issuer.example.com/")
    oidc_audience: str = Field(
        default="ai-ml-production-capstone-api", min_length=1, max_length=256
    )
    oidc_jwks_url: HttpUrl | str = Field(
        default="https://issuer.example.com/.well-known/jwks.json"
    )
    allowed_jwt_algorithms: tuple[str, ...] = ("RS256",)
    cors_origins: str = "*"

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = value.replace("postgres://", "postgresql+asyncpg://", 1)
        elif value.startswith("postgresql://") and not value.startswith(
            "postgresql+asyncpg://"
        ):
            value = value.replace("postgresql://", "postgresql+asyncpg://", 1)

        if not value.startswith("postgresql+asyncpg://"):
            msg = "DATABASE_URL must use the postgresql+asyncpg scheme."
            raise ValueError(msg)
        if "sslmode=" in value:
            value = value.replace("sslmode=", "ssl=")
        return value

    @field_validator("allowed_jwt_algorithms", mode="before")
    @classmethod
    def parse_algorithms(cls, value: str | tuple[str, ...]) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(item.strip() for item in value.split(",") if item.strip())
        return value

    @field_validator("allowed_jwt_algorithms")
    @classmethod
    def validate_algorithms(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        supported = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
        if not value or not set(value).issubset(supported):
            msg = "ALLOWED_JWT_ALGORITHMS must contain supported asymmetric algorithms."
            raise ValueError(msg)
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached process-wide settings after validation."""

    return Settings()
