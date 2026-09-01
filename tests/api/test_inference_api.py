"""API and end-to-end integration tests for real-time model inference sandbox."""

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


def setup_mock_inference_db(
    app: FastAPI,
    user: User,
    membership: WorkspaceMembership | None,
    model_get: ModelVersion | None = None,
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

    def execute_side_effect(query: object) -> MagicMock:
        query_str = str(query)
        if "FROM users" in query_str:
            return user_result
        if "FROM workspace_memberships" in query_str:
            return membership_result
        if "FROM model_versions" in query_str:
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
async def test_predict_unauthenticated(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)
    model_id = uuid4()
    workspace_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/predict",
            json={
                "workspace_id": str(workspace_id),
                "input_features": {"age": 30, "income": 50000},
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_predict_workspace_isolation_cross_workspace(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    user_ws_id = uuid4()
    other_ws_id = uuid4()
    model_id = uuid4()
    now = datetime.now(UTC)

    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=user_ws_id, user_id=user.id, role="viewer"
    )

    # Model belongs to OTHER workspace
    model = ModelVersion(
        id=model_id,
        workspace_id=other_ws_id,
        name="other-model",
        version_tag="v1.0.0",
        artifact_path="models/other-model/v1.0.0.json",
        status="production",
        created_at=now,
        updated_at=now,
    )

    setup_mock_inference_db(app, user=user, membership=membership, model_get=model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/predict",
            json={
                "workspace_id": str(user_ws_id),
                "input_features": {"age": 30},
            },
            headers={"Authorization": "Bearer token"},
        )

    # Fails closed with 404 Not Found to prevent leaking model existence across workspaces
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_predict_rejected_model_blocked(
    test_settings: Settings, mock_principal: Principal, tmp_path
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

    # Model is REJECTED
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

    setup_mock_inference_db(app, user=user, membership=membership, model_get=model)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/models/{model_id}/predict",
            json={
                "workspace_id": str(workspace_id),
                "input_features": {"age": 35, "income": 50000, "tenure": 4},
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    assert "Inference unavailable" in response.json()["detail"]


@pytest.mark.asyncio
async def test_real_end_to_end_training_to_inference_flow(
    test_settings: Settings, mock_principal: Principal, tmp_path
) -> None:
    """Real End-to-End Test:

    Ingest CSV -> Train RandomForest -> Save SHA-256 Artifact -> Promote to Production ->
    Execute Predict API -> Verify Prediction, Confidence, & Latency!
    """
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    model_id = uuid4()
    now = datetime.now(UTC)

    # 1. Train real model using ModelTrainer and write real artifact
    store = ArtifactStore(base_dir=tmp_path)
    trainer = ModelTrainer(artifact_store=store)

    csv_data = (
        "age,income,tenure,churn\n"
        "25,30000,1,0\n50,90000,5,1\n22,25000,1,0\n45,80000,4,1\n"
        "28,35000,2,0\n55,95000,6,1\n30,40000,3,0\n60,100000,7,1\n"
        "32,42000,3,0\n58,98000,6,1\n"
    )
    csv_file = tmp_path / "train_churn.csv"
    csv_file.write_text(csv_data, encoding="utf-8")

    metrics, artifact_key = trainer.train_dataset_model(
        csv_file_path=str(csv_file),
        target_column="churn",
        model_name="real-churn-model",
        version_tag="v1.0.0",
        model_type="random_forest",
    )

    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    model = ModelVersion(
        id=model_id,
        workspace_id=workspace_id,
        name="real-churn-model",
        version_tag="v1.0.0",
        artifact_path=artifact_key,
        status="production",  # Promoted to production
        metrics_json=metrics,
        created_at=now,
        updated_at=now,
    )

    setup_mock_inference_db(app, user=user, membership=membership, model_get=model)

    from app.api.routers.ml import _ml_service

    orig_store = _ml_service._predictor.artifact_store
    _ml_service._predictor.artifact_store = store
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                f"/api/v1/models/{model_id}/predict",
                json={
                    "workspace_id": str(workspace_id),
                    "input_features": {"age": 52, "income": 92000, "tenure": 5},
                },
                headers={"Authorization": "Bearer token"},
            )
    finally:
        _ml_service._predictor.artifact_store = orig_store

    assert response.status_code == 200
    data = response.json()

    assert data["model_id"] == str(model_id)
    assert data["model_version"] == "v1.0.0"
    assert "prediction" in data
    assert 0.0 <= data["confidence"] <= 1.0
    assert data["latency_ms"] > 0.0
