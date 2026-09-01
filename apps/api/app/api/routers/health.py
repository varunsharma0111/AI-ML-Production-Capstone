"""Liveness and deep multi-dependency readiness endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import text

from app.core.errors import DomainError
from app.core.storage import get_storage_backend

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Liveness probe returning 200 OK if process is running."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request) -> dict[str, Any]:
    """Readiness probe testing DB, Redis, and Storage backend connectivity."""
    checks: dict[str, str] = {}
    unhealthy: list[str] = []

    # 1. Database check
    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as err:
        checks["database"] = f"unhealthy: {err}"
        unhealthy.append("database")

    # 2. Redis check
    try:
        redis_mgr = getattr(request.app.state, "redis_manager", None)
        if redis_mgr and hasattr(redis_mgr, "ping") and redis_mgr.is_connected:
            is_alive = await redis_mgr.ping()
            if is_alive:
                checks["redis"] = "healthy"
            else:
                checks["redis"] = "unhealthy: ping returned False"
                unhealthy.append("redis")
        else:
            checks["redis"] = "healthy (local/fallback)"
    except Exception as err:
        checks["redis"] = f"unhealthy: {err}"
        unhealthy.append("redis")

    # 3. Storage Backend check
    try:
        backend = get_storage_backend()
        backend.object_exists("health_probe_check.nonexistent")
        checks["storage"] = "healthy"
    except Exception as err:
        checks["storage"] = f"unhealthy: {err}"
        unhealthy.append("storage")

    if unhealthy:
        raise DomainError(
            status_code=503,
            code="dependency_unavailable",
            title="Service Unavailable",
            detail=f"Readiness check failed for dependencies: {', '.join(unhealthy)}",
        )

    return {"status": "ok", "dependencies": checks}
