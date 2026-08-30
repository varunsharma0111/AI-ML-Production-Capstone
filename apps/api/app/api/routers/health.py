"""Liveness and database-readiness endpoints."""

from app.core.errors import DomainError
from fastapi import APIRouter, Request
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(request: Request) -> dict[str, str]:
    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as error:
        raise DomainError(
            503, "dependency_unavailable", "Service Unavailable", "Database unavailable."
        ) from error
    return {"status": "ok"}
