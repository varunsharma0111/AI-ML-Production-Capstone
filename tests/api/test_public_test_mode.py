"""Tests for PUBLIC_TEST_MODE feature flag, security resolution, and public workflow support."""

from __future__ import annotations

from uuid import UUID, uuid4

import httpx
import pytest

from app.core.config import Settings
from app.db.models.entities import User, WorkspaceMembership
from app.db.repositories.identity import PUBLIC_TEST_WORKSPACE_ID
from app.main import create_app
from tests.api.test_tasks import setup_mock_db


def test_public_test_mode_defaults_to_false() -> None:
    """Verify PUBLIC_TEST_MODE defaults to False."""
    settings = Settings(
        app_env="local",
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
    )
    assert settings.public_test_mode is False


@pytest.mark.asyncio
async def test_public_test_mode_resolves_public_user() -> None:
    """Verify when PUBLIC_TEST_MODE=true, unauthenticated requests get Public Test User principal."""
    settings = Settings(
        app_env="test",
        public_test_mode=True,
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
    )
    app = create_app(settings=settings)

    public_user = User(
        id=uuid4(),
        oidc_subject="public-test-user-id",
        email="public.test@auraml.local",
        display_name="Public Test User",
    )
    setup_mock_db(app, user=public_user, membership=None)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/me")

    assert response.status_code == 200
    data = response.json()
    assert data["subject"] == "public-test-user-id"
    assert data["email"] == "public.test@auraml.local"
    assert data["display_name"] == "Public Test User"


@pytest.mark.asyncio
async def test_public_test_mode_allows_workspace_access() -> None:
    """Verify PUBLIC_TEST_MODE allows unauthenticated workspace operations."""
    settings = Settings(
        app_env="test",
        public_test_mode=True,
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
    )
    app = create_app(settings=settings)
    workspace_id = PUBLIC_TEST_WORKSPACE_ID
    public_user = User(
        id=uuid4(),
        oidc_subject="public-test-user-id",
        email="public.test@auraml.local",
        display_name="Public Test User",
    )
    membership = WorkspaceMembership(
        workspace_id=workspace_id,
        user_id=public_user.id,
        role="owner",
    )
    setup_mock_db(app, user=public_user, membership=membership)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(f"/api/v1/workspaces/{workspace_id}/tasks")

    assert response.status_code == 200


def test_public_test_mode_fails_in_production_without_override() -> None:
    """Verify PUBLIC_TEST_MODE fails in production without ALLOW_PUBLIC_TEST_IN_PROD=true."""
    with pytest.raises(ValueError, match="PUBLIC_TEST_MODE cannot be enabled in production"):
        Settings(
            app_env="production",
            public_test_mode=True,
            database_url="sqlite+aiosqlite:///:memory:",
            oidc_issuer="https://issuer.example.com/",
            oidc_audience="ai-ml-production-capstone-api",
            oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
        )


def test_public_test_mode_allowed_in_production_with_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify PUBLIC_TEST_MODE is allowed in production when ALLOW_PUBLIC_TEST_IN_PROD=true."""
    monkeypatch.setenv("ALLOW_PUBLIC_TEST_IN_PROD", "true")
    settings = Settings(
        app_env="production",
        public_test_mode=True,
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
    )
    assert settings.public_test_mode is True
