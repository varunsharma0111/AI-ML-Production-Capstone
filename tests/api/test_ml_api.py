"""API tests for ML model registration, evaluation quality gates, and controlled inference."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.db.models.entities import ModelVersion, User, WorkspaceMembership
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


@pytest.fixture
def mock_principal() -> Principal:
    return Principal(
        subject="user_sub_001", email="editor@example.com", display_name="Workspace Editor"
    )


def setup_mock_db(
    app: FastAPI,
    user: User,
    membership: WorkspaceMembership | None,
    model_get: ModelVersion | None = None,
    model_list: list[ModelVersion] | None = None,
) -> AsyncMock:
    mock_session = AsyncMock()

    def add_side_effect(obj: Any) -> None:
        if hasattr(obj, "id") and getattr(obj, "id") is None:
            setattr(obj, "id", uuid4())
        now = datetime.now(UTC)
        if hasattr(obj, "created_at") and getattr(obj, "created_at") is None:
            setattr(obj, "created_at", now)
        if hasattr(obj, "updated_at") and getattr(obj, "updated_at") is None:
            setattr(obj, "updated_at", now)
        table_cols = getattr(getattr(type(obj), "__table__", None), "columns", {})
        if "version" in table_cols and getattr(obj, "version", None) is None:
            setattr(obj, "version", 1)
        if "status" in table_cols and getattr(obj, "status", None) is None:
            setattr(obj, "status", "draft")

    mock_session.add = MagicMock(side_effect=add_side_effect)

    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = MagicMock(return_value=begin_cm)

    async def refresh_side_effect(obj: Any) -> None:
        add_side_effect(obj)

    mock_session.refresh.side_effect = refresh_side_effect

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = membership

    model_get_result = MagicMock()
    model_get_result.scalar_one_or_none.return_value = model_get

    model_list_result = MagicMock()
    model_list_result.scalars.return_value = model_list or []

    def execute_side_effect(query: object) -> MagicMock:
        query_str = str(query)
        if "FROM users" in query_str:
            return user_result
        if "FROM workspace_memberships" in query_str:
            return membership_result
        if "FROM model_versions" in query_str:
            if "ORDER BY" in query_str:
                return model_list_result
            return model_get_result
        return MagicMock()

    mock_session.execute.side_effect = execute_side_effect

    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_context)
    app.state.session_factory = mock_session_factory
    return mock_session


@pytest.mark.asyncio
async def test_register_model_success(test_settings: Settings, mock_principal: Principal) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )
    setup_mock_db(app, user=user, membership=membership)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/models",
            json={
                "workspace_id": str(workspace_id),
                "name": "sentiment_classifier",
                "version_tag": "v1.0.0",
                "description": "Initial draft model",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "sentiment_classifier"
    assert data["status"] == "candidate"


@pytest.mark.asyncio
async def test_evaluate_model_quality_gate_approved(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    model_id = uuid4()
    workspace_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    model = ModelVersion(
        id=model_id,
        workspace_id=workspace_id,
        name="test_model",
        version_tag="v1.0.0",
        artifact_path="artifacts/models/test_model/v1.0.0.json",
        status="candidate",
        created_at=now,
        updated_at=now,
    )

    setup_mock_db(app, user=user, membership=membership, model_get=model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/evaluate",
            json={
                "workspace_id": str(workspace_id),
                "accuracy": 0.92,
                "f1_score": 0.89,
                "latency_ms": 15.0,
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"


@pytest.mark.asyncio
async def test_predict_unapproved_model_rejected(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    model_id = uuid4()
    workspace_id = uuid4()
    now = datetime.now(UTC)

    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    unapproved_model = ModelVersion(
        id=model_id,
        name="draft_model",
        version_tag="v0.1.0",
        artifact_path="artifacts/models/draft_model/v0.1.0.json",
        status="draft",  # Draft model NOT approved
        created_at=now,
        updated_at=now,
    )

    setup_mock_db(app, user=user, membership=membership, model_get=unapproved_model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/predict",
            json={
                "workspace_id": str(workspace_id),
                "input_features": {"feature_1": 0.5, "feature_2": 0.8},
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    assert response.json()["code"] == "model_not_approved"
