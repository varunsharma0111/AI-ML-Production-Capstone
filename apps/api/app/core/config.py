"""Typed, environment-backed application configuration."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or an ignored .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["local", "test", "staging", "production"] = "local"
    app_name: str = "AI/ML Production Capstone API"
    log_level: str = "INFO"
    dev_auth_mode: bool = Field(default=False)
    public_test_mode: bool = Field(default=False)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/capstone"
    )
    database_pool_size: int = Field(default=5, ge=1, le=20)
    database_max_overflow: int = Field(default=5, ge=0, le=20)
    redis_url: str = Field(default="redis://localhost:6379/0")
    oidc_issuer: HttpUrl | str = Field(default="https://issuer.example.com/")
    oidc_audience: str = Field(
        default="ai-ml-production-capstone-api",
        min_length=1,
        max_length=256,
    )
    oidc_jwks_url: HttpUrl | str = Field(
        default="https://issuer.example.com/.well-known/jwks.json",
    )
    allowed_jwt_algorithms: str | tuple[str, ...] = ("RS256",)
    cors_origins: str = "*"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Any) -> Any:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and not v.startswith("postgresql+asyncpg://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @model_validator(mode="after")
    def validate_dev_auth_mode(self) -> Settings:
        if self.app_env == "production" and self.dev_auth_mode:
            raise ValueError("DEV_AUTH_MODE cannot be enabled in production.")
        if self.app_env == "production" and self.public_test_mode:
            import os

            if os.getenv("ALLOW_PUBLIC_TEST_IN_PROD", "").lower() != "true":
                raise ValueError(
                    "PUBLIC_TEST_MODE cannot be enabled in production "
                    "without ALLOW_PUBLIC_TEST_IN_PROD=true."
                )
        return self

    # Storage & Artifact Settings
    storage_backend: Literal["local", "s3"] = "local"
    storage_path: str = "./data/uploads"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "auraml-artifacts"
    s3_region: str = "us-east-1"
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None

    @field_validator("storage_path", mode="after")
    @classmethod
    def resolve_storage_path(cls, value: str) -> str:
        p = Path(value)
        if not p.is_absolute():
            project_root = Path(__file__).resolve().parents[3]
            return str((project_root / p).resolve())
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if value.startswith("postgres://"):
            value = value.replace("postgres://", "postgresql+asyncpg://", 1)
        elif value.startswith("postgresql://"):
            value = value.replace("postgresql://", "postgresql+asyncpg://", 1)

        if not (
            value.startswith("postgresql+asyncpg://")
            or value.startswith("sqlite+aiosqlite://")
            or value.startswith("sqlite://")
        ):
            msg = "DATABASE_URL must use postgresql+asyncpg or sqlite+aiosqlite scheme."
            raise ValueError(msg)
        if "sslmode=" in value:
            value = value.replace("sslmode=", "ssl=")
        return value

    @field_validator("allowed_jwt_algorithms", mode="before")
    @classmethod
    def parse_algorithms(cls, value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            v = value.strip()
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list | tuple):
                        return tuple(str(x).strip() for x in parsed if str(x).strip())
                except Exception:
                    pass
            return tuple(item.strip() for item in v.split(",") if item.strip())
        if isinstance(value, list | tuple):
            return tuple(str(x).strip() for x in value if str(x).strip())
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
