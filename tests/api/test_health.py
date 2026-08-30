"""API tests for liveness and readiness health endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/capstone_test",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
        allowed_jwt_algorithms=("RS256",),
    )


@pytest.mark.asyncio
async def test_liveness_endpoint(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_readiness_endpoint_success(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)

    mock_session = AsyncMock()
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_context)

    app.state.session_factory = mock_session_factory

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_endpoint_database_failure(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)

    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception("Database connection timeout")
    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_context)

    app.state.session_factory = mock_session_factory

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["code"] == "dependency_unavailable"
    assert data["status"] == 503
    assert "Database unavailable" in data["detail"]
