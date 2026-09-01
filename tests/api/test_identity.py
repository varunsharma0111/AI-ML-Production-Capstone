"""API tests for identity and current-user endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

from app.core.config import Settings
from app.core.errors import AuthenticationError
from app.db.models.entities import User
from app.domains.identity.principal import Principal
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
async def test_current_user_unauthenticated(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/me")

    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "authentication_failed"
    assert data["status"] == 401


@pytest.mark.asyncio
async def test_current_user_invalid_token(test_settings: Settings) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.side_effect = AuthenticationError("Invalid signature")

    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/me", headers={"Authorization": "Bearer invalid_token"})

    assert response.status_code == 401
    data = response.json()
    assert data["code"] == "authentication_failed"


@pytest.mark.asyncio
async def test_current_user_success(test_settings: Settings) -> None:
    mock_verifier = MagicMock()
    mock_principal = Principal(
        subject="sub_999", email="user999@example.com", display_name="User Nine Nine Nine"
    )
    mock_verifier.verify.return_value = mock_principal

    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    user_id = uuid4()
    db_user = User(
        id=user_id,
        oidc_subject="sub_999",
        email="user999@example.com",
        display_name="User Nine Nine Nine",
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = MagicMock(return_value=begin_cm)

    mock_user_result = MagicMock()
    mock_user_result.scalar_one_or_none.return_value = db_user

    mock_mem_result = MagicMock()
    mock_mem_result.scalars.return_value.all.return_value = [MagicMock(role="owner")]

    mock_ws_result = MagicMock()
    mock_ws_result.all.return_value = []

    mock_session.execute.side_effect = [mock_user_result, mock_mem_result, mock_ws_result]

    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_context)
    app.state.session_factory = mock_session_factory

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/me", headers={"Authorization": "Bearer valid_token"})

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(user_id)
    assert data["subject"] == "sub_999"
    assert data["email"] == "user999@example.com"
    assert data["display_name"] == "User Nine Nine Nine"
    assert "workspaces" in data
