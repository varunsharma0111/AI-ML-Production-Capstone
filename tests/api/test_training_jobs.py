"""API and integration tests for model training job creation, worker execution, and ModelVersion registration."""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from app.core.config import Settings
from app.db.models.entities import Dataset, DatasetProfile, Job, User, WorkspaceMembership
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


def setup_mock_training_db(
    app: FastAPI,
    user: User,
    membership: WorkspaceMembership | None,
    dataset_get: Dataset | None = None,
    profile_get: DatasetProfile | None = None,
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

    dataset_get_result = MagicMock()
    dataset_get_result.scalar_one_or_none.return_value = dataset_get

    profile_get_result = MagicMock()
    profile_get_result.scalar_one_or_none.return_value = profile_get

    def execute_side_effect(query: object) -> MagicMock:
        query_str = str(query)
        if "FROM users" in query_str:
            return user_result
        if "FROM workspace_memberships" in query_str:
            return membership_result
        if "FROM dataset_profiles" in query_str:
            return profile_get_result
        if "FROM datasets" in query_str:
            return dataset_get_result
        if "FROM jobs" in query_str:
            res = MagicMock()
            res.scalar_one_or_none.return_value = None
            return res
        return MagicMock()

    mock_session.execute.side_effect = execute_side_effect

    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_context)
    app.state.session_factory = mock_session_factory
    return mock_session


@pytest.mark.asyncio
async def test_submit_training_job_unauthenticated(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)
    workspace_id = uuid4()
    dataset_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/jobs/train",
            json={
                "workspace_id": str(workspace_id),
                "dataset_id": str(dataset_id),
                "target_column": "target",
                "model_name": "test-model",
            },
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_training_job_viewer_forbidden(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    dataset_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )

    setup_mock_training_db(app, user=user, membership=membership)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/jobs/train",
            json={
                "workspace_id": str(workspace_id),
                "dataset_id": str(dataset_id),
                "target_column": "target",
                "model_name": "test-model",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_submit_training_job_dataset_not_found(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    dataset_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    setup_mock_training_db(app, user=user, membership=membership, dataset_get=None)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/jobs/train",
            json={
                "workspace_id": str(workspace_id),
                "dataset_id": str(dataset_id),
                "target_column": "target",
                "model_name": "test-model",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_submit_training_job_dataset_not_ready(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    dataset_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    unready_dataset = Dataset(
        id=dataset_id,
        workspace_id=workspace_id,
        created_by_user_id=user.id,
        original_filename="unready.csv",
        storage_path="/data/unready.csv",
        file_size_bytes=100,
        mime_type="text/csv",
        format="csv",
        status="uploaded",
        created_at=now,
        updated_at=now,
    )

    setup_mock_training_db(app, user=user, membership=membership, dataset_get=unready_dataset)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/jobs/train",
            json={
                "workspace_id": str(workspace_id),
                "dataset_id": str(dataset_id),
                "target_column": "target",
                "model_name": "test-model",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    assert "not ready" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_submit_training_job_invalid_target_column(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    dataset_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    dataset = Dataset(
        id=dataset_id,
        workspace_id=workspace_id,
        created_by_user_id=user.id,
        original_filename="sample.csv",
        storage_path="/data/sample.csv",
        file_size_bytes=100,
        mime_type="text/csv",
        format="csv",
        status="ready",
        created_at=now,
        updated_at=now,
    )

    profile = DatasetProfile(
        id=uuid4(),
        dataset_id=dataset_id,
        row_count=10,
        column_count=2,
        columns_json=[
            {"name": "col_a", "inferred_type": "integer"},
            {"name": "col_b", "inferred_type": "string"},
        ],
        created_at=now,
    )

    setup_mock_training_db(
        app, user=user, membership=membership, dataset_get=dataset, profile_get=profile
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/jobs/train",
            json={
                "workspace_id": str(workspace_id),
                "dataset_id": str(dataset_id),
                "target_column": "invalid_column",
                "model_name": "test-model",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    assert "does not exist" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_submit_training_job_success(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    dataset_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    with tempfile.TemporaryDirectory() as tmp_dir:
        csv_file = Path(tmp_dir) / "data.csv"
        csv_file.write_text("feature1,target\n1.0,yes\n2.0,no\n3.0,yes\n4.0,no\n", encoding="utf-8")

        dataset = Dataset(
            id=dataset_id,
            workspace_id=workspace_id,
            created_by_user_id=user.id,
            original_filename="data.csv",
            storage_path=str(csv_file),
            file_size_bytes=100,
            mime_type="text/csv",
            format="csv",
            status="ready",
            created_at=now,
            updated_at=now,
        )

        profile = DatasetProfile(
            id=uuid4(),
            dataset_id=dataset_id,
            row_count=4,
            column_count=2,
            columns_json=[
                {"name": "feature1", "inferred_type": "float"},
                {"name": "target", "inferred_type": "string"},
            ],
            created_at=now,
        )

        setup_mock_training_db(
            app, user=user, membership=membership, dataset_get=dataset, profile_get=profile
        )

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/jobs/train",
                json={
                    "workspace_id": str(workspace_id),
                    "dataset_id": str(dataset_id),
                    "target_column": "target",
                    "model_name": "churn-classifier",
                    "model_type": "random_forest",
                    "hyperparameters": {"n_estimators": 20, "max_depth": 3},
                },
                headers={"Authorization": "Bearer token"},
            )

        assert response.status_code == 201
        data = response.json()
        assert data["job_type"] == "model_training"
        assert data["status"] == "completed"
        assert data["result_json"] is not None
        assert "metrics" in data["result_json"]
        assert "model_version_id" in data["result_json"]
        assert data["result_json"]["model_name"] == "churn-classifier"
        artifact_path = data["result_json"]["artifact_path"]
        assert artifact_path.startswith("models/")
        assert "d:" not in artifact_path.lower()
        assert "c:" not in artifact_path.lower()
