"""API tests for workspace-scoped dataset upload, listing, details, and profiling endpoints."""

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


def setup_mock_dataset_db(
    app: FastAPI,
    user: User,
    membership: WorkspaceMembership | None,
    dataset_get: Dataset | None = None,
    dataset_list: list[Dataset] | None = None,
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

    dataset_list_result = MagicMock()
    dataset_list_result.scalars.return_value = dataset_list or []

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
            if "ORDER BY" in query_str or "OFFSET" in query_str or "LIMIT" in query_str:
                return dataset_list_result
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
async def test_upload_dataset_unauthenticated(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)
    workspace_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/datasets/upload",
            data={"workspace_id": str(workspace_id)},
            files={"file": ("test.csv", b"a,b\n1,2", "text/csv")},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_dataset_invalid_format(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    setup_mock_dataset_db(app, user=user, membership=membership)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/datasets/upload",
            data={"workspace_id": str(workspace_id)},
            files={"file": ("executable.exe", b"binary content", "application/octet-stream")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    data = response.json()
    assert "Only CSV format datasets" in data["detail"]


@pytest.mark.asyncio
async def test_upload_dataset_empty_file(
    test_settings: Settings, mock_principal: Principal
) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    setup_mock_dataset_db(app, user=user, membership=membership)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/datasets/upload",
            data={"workspace_id": str(workspace_id)},
            files={"file": ("empty.csv", b"", "text/csv")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    data = response.json()
    assert "empty" in data["detail"].lower()


@pytest.mark.asyncio
async def test_upload_dataset_viewer_forbidden(
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

    setup_mock_dataset_db(app, user=user, membership=membership)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/datasets/upload",
            data={"workspace_id": str(workspace_id)},
            files={"file": ("data.csv", b"x,y\n1,2", "text/csv")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_upload_dataset_success(test_settings: Settings, mock_principal: Principal) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="editor"
    )

    setup_mock_dataset_db(app, user=user, membership=membership)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/v1/datasets/upload",
            data={"workspace_id": str(workspace_id)},
            files={"file": ("housing.csv", b"price,size\n300000,1500\n450000,2000", "text/csv")},
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 201
    data = response.json()
    assert "dataset" in data
    assert data["dataset"]["original_filename"] == "housing.csv"
    assert data["dataset"]["status"] == "ready"
    assert data["dataset"]["row_count"] == 2
    assert data["dataset"]["column_count"] == 2


@pytest.mark.asyncio
async def test_list_datasets_success(test_settings: Settings, mock_principal: Principal) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )

    existing_datasets = [
        Dataset(
            id=uuid4(),
            workspace_id=workspace_id,
            created_by_user_id=user.id,
            original_filename="metrics.csv",
            storage_path="/data/metrics.csv",
            file_size_bytes=1024,
            mime_type="text/csv",
            format="csv",
            status="ready",
            row_count=100,
            column_count=5,
            created_at=now,
            updated_at=now,
        )
    ]

    setup_mock_dataset_db(app, user=user, membership=membership, dataset_list=existing_datasets)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/v1/datasets?workspace_id={workspace_id}&offset=0&limit=10",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["original_filename"] == "metrics.csv"


@pytest.mark.asyncio
async def test_get_dataset_profile_success(
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
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )

    dataset = Dataset(
        id=dataset_id,
        workspace_id=workspace_id,
        created_by_user_id=user.id,
        original_filename="train.csv",
        storage_path="/data/train.csv",
        file_size_bytes=2048,
        mime_type="text/csv",
        format="csv",
        status="ready",
        row_count=50,
        column_count=2,
        created_at=now,
        updated_at=now,
    )

    profile = DatasetProfile(
        id=uuid4(),
        dataset_id=dataset_id,
        row_count=50,
        column_count=2,
        columns_json=[
            {
                "name": "col_a",
                "inferred_type": "integer",
                "missing_count": 0,
                "missing_percentage": 0.0,
                "unique_count": 50,
                "min_value": 1,
                "max_value": 50,
                "mean_value": 25.5,
            }
        ],
        created_at=now,
    )

    setup_mock_dataset_db(
        app, user=user, membership=membership, dataset_get=dataset, profile_get=profile
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/v1/datasets/{dataset_id}/profile?workspace_id={workspace_id}",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["dataset_id"] == str(dataset_id)
    assert data["row_count"] == 50
    assert len(data["columns_json"]) == 1
    assert data["columns_json"][0]["name"] == "col_a"
