"""Security tests for WebSocket router endpoint authentication and authorization."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.models.entities import User, WorkspaceMembership
from app.domains.identity.principal import Principal
from app.main import create_app


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite:///:memory:",
        oidc_issuer="https://issuer.example.com/",
        oidc_audience="ai-ml-production-capstone-api",
        oidc_jwks_url="https://issuer.example.com/.well-known/jwks.json",
        allowed_jwt_algorithms=("RS256",),
    )


def test_websocket_missing_token(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)
    client = TestClient(app)
    workspace_id = uuid4()

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/v1/workspaces/{workspace_id}/jobs"):
            pass


def test_websocket_invalid_token(test_settings: Settings) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.side_effect = ValueError("Invalid signature")
    app = create_app(settings=test_settings, token_verifier=mock_verifier)
    client = TestClient(app)
    workspace_id = uuid4()

    with pytest.raises(Exception):
        with client.websocket_connect(f"/ws/v1/workspaces/{workspace_id}/jobs?token=bad_token"):
            pass


def test_websocket_authorized_success(test_settings: Settings) -> None:
    principal = Principal(subject="sub_123", email="user@example.com", display_name="User")
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = principal

    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user_id = uuid4()
    user = User(id=user_id, oidc_subject=principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user_id, role="editor"
    )

    mock_session = AsyncMock()
    user_res = MagicMock()
    user_res.scalar_one_or_none.return_value = user
    mem_res = MagicMock()
    mem_res.scalar_one_or_none.return_value = membership

    def execute_side_effect(query: object) -> MagicMock:
        q = str(query)
        if "FROM users" in q:
            return user_res
        if "FROM workspace_memberships" in q:
            return mem_res
        return MagicMock()

    mock_session.execute.side_effect = execute_side_effect

    session_ctx = MagicMock()
    session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    session_ctx.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=session_ctx)
    app.state.session_factory = mock_factory

    client = TestClient(app)
    with client.websocket_connect(
        f"/ws/v1/workspaces/{workspace_id}/jobs?token=valid_token"
    ) as websocket:
        data = websocket.receive_json()
        assert data["event"] == "connection_established"
        assert data["workspace_id"] == str(workspace_id)

        websocket.send_text("ping")
        resp = websocket.receive_json()
        assert resp["event"] == "pong"
