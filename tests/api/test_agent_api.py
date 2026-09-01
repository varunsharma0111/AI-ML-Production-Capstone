"""Tests for AI Agent Assistant & Analytics Workspace."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from agent.tools.security import AgentToolSecurityGuard
from app.core.config import Settings
from app.core.errors import DomainError
from app.db.models.entities import ModelVersion, User, WorkspaceMembership
from app.domains.identity.principal import Principal
from app.main import create_app
from ml.artifacts.store import ArtifactStore
from ml.training.trainer import ModelTrainer


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
        subject="user_sub_001", email="user@example.com", display_name="Workspace User"
    )


def setup_mock_agent_db(
    app: FastAPI,
    user: User,
    membership: WorkspaceMembership | None,
    models: list[ModelVersion] | None = None,
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
    model_get_result.scalar_one_or_none.return_value = models[0] if models else None

    models_list_result = MagicMock()
    models_list_result.scalars.return_value = models or []
    models_list_result.scalar_one_or_none.return_value = models[0] if models else None

    datasets_result = MagicMock()
    datasets_result.scalars.return_value = []

    eval_result = MagicMock()
    eval_result.scalar_one_or_none.return_value = None

    def execute_side_effect(query: object) -> MagicMock:
        query_str = str(query)
        if "FROM users" in query_str:
            return user_result
        if "FROM workspace_memberships" in query_str:
            return membership_result
        if "FROM model_versions" in query_str:
            if "ORDER BY" in query_str or "workspace_id" in query_str:
                return models_list_result
            return model_get_result
        if "FROM model_evaluations" in query_str:
            return eval_result
        if "FROM datasets" in query_str:
            return datasets_result
        return MagicMock()

    mock_session.execute.side_effect = execute_side_effect

    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_context)
    app.state.session_factory = mock_session_factory
    return mock_session


@pytest.mark.asyncio
async def test_agent_orchestrate_unauthenticated(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)
    workspace_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/agent/orchestrate",
            json={
                "workspace_id": str(workspace_id),
                "message": "Compare churn model v1 and v2",
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_agent_orchestrate_workspace_isolation_denied(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)

    # User has NO membership in requested workspace
    setup_mock_agent_db(app, user=user, membership=None)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/agent/orchestrate",
            json={
                "workspace_id": str(workspace_id),
                "message": "Compare churn model v1 and v2",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 403


def test_agent_tool_security_path_traversal_attempt() -> None:
    """Security Test: Rejects path traversal attempt in agent tool arguments."""
    guard = AgentToolSecurityGuard()
    with pytest.raises(DomainError) as exc_info:
        guard.validate_input_string("../../etc/passwd", field_name="expression")
    assert "unsafe path traversal" in exc_info.value.detail


def test_agent_tool_security_command_injection_attempt() -> None:
    """Security Test: Rejects shell injection characters in agent tool arguments."""
    guard = AgentToolSecurityGuard()
    with pytest.raises(DomainError) as exc_info:
        guard.validate_input_string("100; rm -rf /", field_name="expression")
    assert "disallowed characters" in exc_info.value.detail


@pytest.mark.asyncio
async def test_agent_orchestrate_compare_models(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )

    now = datetime.now(UTC)
    m1 = ModelVersion(
        id=uuid4(),
        workspace_id=workspace_id,
        name="churn-model",
        version_tag="v1.0.0",
        artifact_path="models/churn/v1.json",
        status="approved",
        metrics_json={"accuracy": 0.88, "f1_score": 0.84, "precision": 0.85, "recall": 0.83},
        created_at=now,
        updated_at=now,
    )
    m2 = ModelVersion(
        id=uuid4(),
        workspace_id=workspace_id,
        name="churn-model",
        version_tag="v2.0.0",
        artifact_path="models/churn/v2.json",
        status="production",
        metrics_json={"accuracy": 0.95, "f1_score": 0.92, "precision": 0.94, "recall": 0.90},
        created_at=now,
        updated_at=now,
    )

    setup_mock_agent_db(app, user=user, membership=membership, models=[m1, m2])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/agent/orchestrate",
            json={
                "workspace_id": str(workspace_id),
                "message": "Compare churn model v1 and v2",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "compare_models" in data["tools_used"]
    assert "v2.0.0" in data["answer"]
    assert "Winner" in data["answer"]


@pytest.mark.asyncio
async def test_agent_orchestrate_explain_metrics(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )

    now = datetime.now(UTC)
    m1 = ModelVersion(
        id=uuid4(),
        workspace_id=workspace_id,
        name="churn-model",
        version_tag="v2.0.0",
        artifact_path="models/churn/v2.json",
        status="rejected",
        metrics_json={"accuracy": 0.82, "f1_score": 0.79},
        created_at=now,
        updated_at=now,
    )

    setup_mock_agent_db(app, user=user, membership=membership, models=[m1])

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/agent/orchestrate",
            json={
                "workspace_id": str(workspace_id),
                "message": "Why did churn-model fail quality gate?",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "explain_metrics" in data["tools_used"]
    assert "REJECTED" in data["answer"]


@pytest.mark.asyncio
async def test_real_agent_prediction_end_to_end(
    test_settings: Settings, mock_principal: Principal, tmp_path
) -> None:
    """REAL END-TO-END TEST:
    Agent calls real inference engine on actual trained model artifact!
    """
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    # Train real model with trainer
    store = ArtifactStore(base_dir=tmp_path)
    trainer = ModelTrainer(artifact_store=store)

    csv_data = (
        "age,income,tenure,churn\n"
        "25,30000,1,0\n50,90000,5,1\n22,25000,1,0\n45,80000,4,1\n"
        "28,35000,2,0\n55,95000,6,1\n30,40000,3,0\n60,100000,7,1\n"
        "32,42000,3,0\n58,98000,6,1\n"
    )
    csv_file = tmp_path / "agent_churn.csv"
    csv_file.write_text(csv_data, encoding="utf-8")

    metrics, artifact_path = trainer.train_dataset_model(
        csv_file_path=str(csv_file),
        target_column="churn",
        model_name="real-agent-model",
        version_tag="v1.0.0",
        model_type="random_forest",
    )

    now = datetime.now(UTC)
    model = ModelVersion(
        id=uuid4(),
        workspace_id=workspace_id,
        name="real-agent-model",
        version_tag="v1.0.0",
        artifact_path=artifact_path,
        status="production",  # Allowed status
        metrics_json=metrics,
        created_at=now,
        updated_at=now,
    )

    setup_mock_agent_db(app, user=user, membership=membership, models=[model])

    from app.api.routers.agent import _agent_service

    orig_store = _agent_service._ml_service._predictor.artifact_store
    _agent_service._ml_service._predictor.artifact_store = store
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/agent/orchestrate",
                json={
                    "workspace_id": str(workspace_id),
                    "message": "Predict churn for age 52, income 92000, tenure 5",
                },
                headers={"Authorization": "Bearer token"},
            )
    finally:
        _agent_service._ml_service._predictor.artifact_store = orig_store

    assert response.status_code == 200
    data = response.json()
    assert "run_prediction" in data["tools_used"]
    assert "Real-Time Inference Output" in data["answer"]
    assert "Confidence Score" in data["answer"]
