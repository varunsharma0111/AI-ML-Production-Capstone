"""API tests for workspace-scoped job submission, list, query, cancellation, and idempotency."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import Settings
from app.db.models.entities import Job, User, WorkspaceMembership
from app.domains.identity.principal import Principal
from app.domains.jobs.types import JobStatus, JobType
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


@pytest.fixture
def mock_principal() -> Principal:
    return Principal(
        subject="user_sub_001", email="editor@example.com", display_name="Workspace Editor"
    )


def setup_mock_db(
    app: FastAPI,
    user: User,
    membership: WorkspaceMembership | None,
    job_get: Job | None = None,
    job_list: list[Job] | None = None,
    idempotency_job: Job | None = None,
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
        if "max_retries" in table_cols and getattr(obj, "max_retries", None) is None:
            setattr(obj, "max_retries", 3)
        if "attempt_count" in table_cols and getattr(obj, "attempt_count", None) is None:
            setattr(obj, "attempt_count", 0)
        if "status" in table_cols and getattr(obj, "status", None) is None:
            setattr(obj, "status", "queued")

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

    job_get_result = MagicMock()
    job_get_result.scalar_one_or_none.return_value = job_get

    job_list_result = MagicMock()
    job_list_result.scalars.return_value = job_list or []

    idempotency_result = MagicMock()
    idempotency_result.scalar_one_or_none.return_value = idempotency_job

    def execute_side_effect(query: object) -> MagicMock:
        query_str = str(query)
        if "FROM users" in query_str:
            return user_result
        if "FROM workspace_memberships" in query_str:
            return membership_result
        if "FROM jobs" in query_str:
            if "idempotency_key =" in query_str or "idempotency_key IS" in query_str:
                return idempotency_result
            if "ORDER BY" in query_str or "OFFSET" in query_str or "LIMIT" in query_str:
                return job_list_result
            return job_get_result
        return MagicMock()

    mock_session.execute.side_effect = execute_side_effect

    mock_context = MagicMock()
    mock_context.__aenter__ = AsyncMock(return_value=mock_session)
    mock_context.__aexit__ = AsyncMock(return_value=None)
    mock_session_factory = MagicMock(return_value=mock_context)
    app.state.session_factory = mock_session_factory
    return mock_session


@pytest.mark.asyncio
async def test_submit_job_unauthenticated(test_settings: Settings) -> None:
    app = create_app(settings=test_settings)
    workspace_id = uuid4()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/jobs",
            json={"job_type": "sample_ml_ingestion", "payload": {}},
        )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_submit_job_success(test_settings: Settings, mock_principal: Principal) -> None:
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
            f"/api/v1/workspaces/{workspace_id}/jobs",
            json={
                "job_type": "sample_ml_ingestion",
                "payload": {"batch_size": 500},
                "idempotency_key": "job_key_999",
            },
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["job_type"] == "sample_ml_ingestion"
    assert data["status"] in ("completed", "queued", "processing")
    assert data["idempotency_key"] == "job_key_999"


@pytest.mark.asyncio
async def test_list_jobs_success(test_settings: Settings, mock_principal: Principal) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    now = datetime.now(UTC)
    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="viewer"
    )

    existing_jobs = [
        Job(
            id=uuid4(),
            workspace_id=workspace_id,
            created_by_user_id=user.id,
            job_type=JobType.DATA_EXPORT.value,
            payload_json={},
            status=JobStatus.COMPLETED.value,
            max_retries=3,
            attempt_count=1,
            version=1,
            created_at=now,
            updated_at=now,
        )
    ]

    setup_mock_db(app, user=user, membership=membership, job_list=existing_jobs)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get(
            f"/api/v1/workspaces/{workspace_id}/jobs?offset=0&limit=10",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["job_type"] == "data_export"


@pytest.mark.asyncio
async def test_cancel_job_success(test_settings: Settings, mock_principal: Principal) -> None:
    mock_verifier = MagicMock()
    mock_verifier.verify.return_value = mock_principal
    app = create_app(settings=test_settings, token_verifier=mock_verifier)

    workspace_id = uuid4()
    job_id = uuid4()
    now = datetime.now(UTC)

    user = User(id=uuid4(), oidc_subject=mock_principal.subject)
    membership = WorkspaceMembership(
        id=uuid4(), workspace_id=workspace_id, user_id=user.id, role="owner"
    )

    existing_job = Job(
        id=job_id,
        workspace_id=workspace_id,
        created_by_user_id=user.id,
        job_type=JobType.MODEL_EVALUATION.value,
        payload_json={},
        status=JobStatus.QUEUED.value,
        max_retries=3,
        attempt_count=0,
        version=1,
        created_at=now,
        updated_at=now,
    )

    setup_mock_db(app, user=user, membership=membership, job_get=existing_job)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            f"/api/v1/workspaces/{workspace_id}/jobs/{job_id}/cancel",
            headers={"Authorization": "Bearer token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "cancelled"
