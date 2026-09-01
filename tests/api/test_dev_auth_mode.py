"""Tests for DEV_AUTH_MODE environment variable, security validation, and behavior."""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.db.models.entities import User
from app.main import create_app
from tests.api.test_tasks import setup_mock_db


def test_production_fails_closed_when_dev_auth_mode_enabled() -> None:
    """Verify system fails closed if DEV_AUTH_MODE=True in production environment."""
    with pytest.raises(ValidationError, match="DEV_AUTH_MODE cannot be enabled in production"):
        Settings(
            app_env="production",
            dev_auth_mode=True,
            database_url="sqlite+aiosqlite:///:memory:",
            oidc_issuer="https://issuer.example.com/",
            oidc_audience="ai-ml-production-capstone-api",
            oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
        )


def test_dev_auth_mode_defaults_to_false() -> None:
    """Verify DEV_AUTH_MODE defaults to False."""
    settings = Settings(
        app_env="local",
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
    )
    assert settings.dev_auth_mode is False


@pytest.mark.asyncio
async def test_production_mode_rejects_unauthenticated_request() -> None:
    """Verify when DEV_AUTH_MODE=false, unauthenticated requests return 401."""
    settings = Settings(
        app_env="local",
        dev_auth_mode=False,
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
    )
    app = create_app(settings=settings)
    workspace_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/v1/workspaces/{workspace_id}/tasks")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_failed"


@pytest.mark.asyncio
async def test_dev_auth_mode_resolves_deterministic_user() -> None:
    """Verify when DEV_AUTH_MODE=true locally, unauthenticated request gets DEV user principal."""
    settings = Settings(
        app_env="local",
        dev_auth_mode=True,
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
    )
    app = create_app(settings=settings)

    dev_user = User(
        id=uuid4(),
        oidc_subject="dev-user-123",
        email="dev.user@example.com",
        display_name="Dev Demo User",
    )
    setup_mock_db(app, user=dev_user, membership=None)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/me")

    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "dev-user-123"
    assert data["email"] == "dev.user@example.com"
    assert data["display_name"] == "Dev Demo User"


@pytest.mark.asyncio
async def test_dev_auth_mode_non_member_workspace_access_returns_403() -> None:
    """Verify DEV_AUTH_MODE enforces workspace authorization and returns 403."""
    settings = Settings(
        app_env="local",
        dev_auth_mode=True,
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
    )
    app = create_app(settings=settings)
    workspace_id = uuid4()

    dev_user = User(
        id=uuid4(),
        oidc_subject="dev-user-123",
        email="dev.user@example.com",
        display_name="Dev Demo User",
    )
    # Membership None simulates requesting a workspace where user has no membership
    setup_mock_db(app, user=dev_user, membership=None)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/v1/workspaces/{workspace_id}/tasks")

    assert response.status_code == 403
    assert response.json()["code"] == "permission_denied"
