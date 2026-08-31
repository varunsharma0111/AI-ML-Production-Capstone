"""API and integration tests for Quality Gate evaluation, model promotion, RBAC, state transitions, and audit certificates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from app.core.config import Settings
from app.db.models.entities import ModelEvaluation, ModelVersion, User, WorkspaceMembership
from app.domains.identity.principal import Principal
from app.main import create_app
from fastapi import FastAPI


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://postgres:postgres@localhost:5432/capstone_test",
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


def setup_mock_ml_db(
    app: FastAPI,
    user: User,
    membership: WorkspaceMembership | None,
    model_get: ModelVersion | None = None,
    model_list: list[ModelVersion] | None = None,
    evaluation_get: ModelEvaluation | None = None,
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

    mock_session.add = MagicMock(side_effect=add_side_effect)

    begin_cm = MagicMock()
    begin_cm.__aenter__ = AsyncMock(return_value=None)
    begin_cm.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin = MagicMock(return_value=begin_cm)

    user_result = MagicMock()
    user_result.scalar_one_or_none.return_value = user

    membership_result = MagicMock()
    membership_result.scalar_one_or_none.return_value = membership

    model_get_result = MagicMock()
    model_get_result.scalar_one_or_none.return_value = model_get

    model_list_result = MagicMock()
    model_list_result.scalars.return_value = model_list or []

    eval_get_result = MagicMock()
    eval_get_result.scalar_one_or_none.return_value = evaluation_get

    def execute_side_effect(query: object) -> MagicMock:
        query_str = str(query)
        if "FROM users" in query_str:
            return user_result
        if "FROM workspace_memberships" in query_str:
            return membership_result
        if "FROM model_evaluations" in query_str:
            return eval_get_result
        if "FROM model_versions" in query_str:
            if "ORDER BY" in query_str and ("workspace_id" in query_str or "WHERE" not in query_str):
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
async def test_evaluate_model_viewer_forbidden(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    model_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )

    setup_mock_ml_db(app, user=user, membership=membership)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/evaluate",
            json={
                "workspace_id": str(workspace_id),
                "accuracy": 0.95,
                "f1_score": 0.90,
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_evaluate_model_passed_approved(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    model_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    model = ModelVersion(
        id=model_id,
        workspace_id=workspace_id,
        name="churn-clf",
        version_tag="v1.0.0",
        artifact_path="models/churn-clf/v1.0.0.json",
        status="candidate",
        metrics_json={"accuracy": 0.92, "f1_score": 0.88},
        created_at=now,
        updated_at=now,
    )

    setup_mock_ml_db(app, user=user, membership=membership, model_get=model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/evaluate",
            json={
                "workspace_id": str(workspace_id),
                "accuracy": 0.92,
                "f1_score": 0.88,
                "accuracy_threshold": 0.90,
                "f1_threshold": 0.85,
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"


@pytest.mark.asyncio
async def test_evaluate_model_failed_rejected(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    model_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    model = ModelVersion(
        id=model_id,
        workspace_id=workspace_id,
        name="churn-clf",
        version_tag="v1.0.0",
        artifact_path="models/churn-clf/v1.0.0.json",
        status="candidate",
        metrics_json={"accuracy": 0.85, "f1_score": 0.78},
        created_at=now,
        updated_at=now,
    )

    setup_mock_ml_db(app, user=user, membership=membership, model_get=model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/evaluate",
            json={
                "workspace_id": str(workspace_id),
                "accuracy": 0.85,
                "f1_score": 0.78,
                "accuracy_threshold": 0.90,
                "f1_threshold": 0.85,
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"


@pytest.mark.asyncio
async def test_promote_rejected_model_forbidden(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    model_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    model = ModelVersion(
        id=model_id,
        workspace_id=workspace_id,
        name="churn-clf",
        version_tag="v1.0.0",
        artifact_path="models/churn-clf/v1.0.0.json",
        status="rejected",
        created_at=now,
        updated_at=now,
    )

    setup_mock_ml_db(app, user=user, membership=membership, model_get=model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/promote",
            json={
                "workspace_id": str(workspace_id),
                "target_status": "staging",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    assert "cannot promote a rejected" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_promote_unapproved_candidate_model_forbidden(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    model_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    model = ModelVersion(
        id=model_id,
        workspace_id=workspace_id,
        name="churn-clf",
        version_tag="v1.0.0",
        artifact_path="models/churn-clf/v1.0.0.json",
        status="candidate",
        created_at=now,
        updated_at=now,
    )

    setup_mock_ml_db(app, user=user, membership=membership, model_get=model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/promote",
            json={
                "workspace_id": str(workspace_id),
                "target_status": "staging",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    assert "must pass quality gate" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_promote_approved_to_staging_success(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    model_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    model = ModelVersion(
        id=model_id,
        workspace_id=workspace_id,
        name="churn-clf",
        version_tag="v1.0.0",
        artifact_path="models/churn-clf/v1.0.0.json",
        status="approved",
        created_at=now,
        updated_at=now,
    )

    setup_mock_ml_db(app, user=user, membership=membership, model_get=model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/promote",
            json={
                "workspace_id": str(workspace_id),
                "target_status": "staging",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "staging"


@pytest.mark.asyncio
async def test_promote_to_production_editor_forbidden(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    model_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    model = ModelVersion(
        id=model_id,
        workspace_id=workspace_id,
        name="churn-clf",
        version_tag="v1.0.0",
        artifact_path="models/churn-clf/v1.0.0.json",
        status="staging",
        created_at=now,
        updated_at=now,
    )

    setup_mock_ml_db(app, user=user, membership=membership, model_get=model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/promote",
            json={
                "workspace_id": str(workspace_id),
                "target_status": "production",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_promote_to_production_owner_success(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    model_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="owner"
    )

    model = ModelVersion(
        id=model_id,
        workspace_id=workspace_id,
        name="churn-clf",
        version_tag="v1.0.0",
        artifact_path="models/churn-clf/v1.0.0.json",
        status="staging",
        created_at=now,
        updated_at=now,
    )

    setup_mock_ml_db(app, user=user, membership=membership, model_get=model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/promote",
            json={
                "workspace_id": str(workspace_id),
                "target_status": "production",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "production"


@pytest.mark.asyncio
async def test_get_quality_gate_viewer_allowed(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    model_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )

    model = ModelVersion(
        id=model_id,
        workspace_id=workspace_id,
        name="churn-clf",
        version_tag="v1.0.0",
        artifact_path="models/churn-clf/v1.0.0.json",
        status="approved",
        created_at=now,
        updated_at=now,
    )

    evaluation = ModelEvaluation(
        id=uuid4(),
        model_version_id=model_id,
        workspace_id=workspace_id,
        accuracy=0.94,
        f1_score=0.89,
        latency_ms=12.5,
        passed_gate=True,
        evaluation_metadata={
            "status": "APPROVED",
            "accuracy_threshold": 0.90,
            "f1_threshold": 0.85,
            "failure_reasons": [],
        },
        evaluated_at=now,
    )

    setup_mock_ml_db(
        app, user=user, membership=membership, model_get=model, evaluation_get=evaluation
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/v1/models/{model_id}/quality-gate?workspace_id={workspace_id}",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == str(model_id)
    assert data["passed_gate"] is True
    assert data["accuracy"] == 0.94
    assert data["f1_score"] == 0.89
