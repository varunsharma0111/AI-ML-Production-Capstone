"""FastAPI application factory for the Phase 2 modular monolith."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure workspace root and apps/api directory are present in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
_API_DIR = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if str(_API_DIR) not in sys.path:
    sys.path.insert(0, str(_API_DIR))

# ruff: noqa: E402

import logging
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.routers import agent, datasets, health, identity, jobs, ml, tasks, websocket
from app.core.config import Settings, get_settings
from app.core.errors import DomainError
from app.core.logging import configure_logging
from app.core.redis import RedisManager
from app.core.security import JwtVerifier
from app.db.session import create_database_engine, create_session_factory

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)


def problem_response(
    request: Request, status_code: int, code: str, title: str, detail: str
) -> JSONResponse:
    """Return a consistent client-safe error with the correlation identifier."""

    request_id = getattr(request.state, "request_id", "unknown")
    headers: dict[str, str] = {}
    origin = request.headers.get("origin")
    if origin:
        headers["Access-Control-Allow-Origin"] = origin
        headers["Access-Control-Allow-Credentials"] = "true"

    return JSONResponse(
        status_code=status_code,
        content={
            "status": status_code,
            "code": code,
            "title": title,
            "detail": detail,
            "request_id": request_id,
        },
        headers=headers,
    )


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach correlation identifier and log basic request details."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        candidate = request.headers.get("X-Request-ID")
        try:
            request_id = str(UUID(candidate)) if candidate else str(uuid4())
        except ValueError:
            request_id = str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_complete",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        return cast(Response, response)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject defensive HTTP security headers into all API responses."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return cast(Response, response)


def create_app(
    settings: Settings | None = None, token_verifier: JwtVerifier | None = None
) -> FastAPI:
    """Create an API app with isolated settings and dependency state for tests."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)
    engine = create_database_engine(resolved_settings)
    redis_manager = RedisManager(resolved_settings.redis_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        await redis_manager.connect()
        try:
            async with engine.begin() as conn:
                from app.db.models.base import Base
                import app.db.models.entities  # noqa: F401

                await conn.run_sync(Base.metadata.create_all)
        except Exception as exc:
            logger.warning("Database schema check warning: %s", exc)
        yield
        await redis_manager.close()
        await engine.dispose()

    app = FastAPI(title=resolved_settings.app_name, lifespan=lifespan)
    app.state.settings = resolved_settings
    app.state.session_factory = create_session_factory(engine)
    app.state.token_verifier = token_verifier or JwtVerifier(resolved_settings)
    app.state.redis_manager = redis_manager
    from app.core.rate_limit import RateLimitMiddleware

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware)

    from fastapi.middleware.cors import CORSMiddleware

    origins = [o.strip() for o in resolved_settings.cors_origins.split(",") if o.strip()]
    default_allowed_origins = [
        "https://ai-ml-production-capstone.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ]
    if "*" in origins:
        origins = default_allowed_origins

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"^https://ai-ml-production-capstone.*\.vercel\.app$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, error: DomainError) -> JSONResponse:
        return problem_response(request, error.status_code, error.code, error.title, error.detail)

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        fields = [".".join(str(part) for part in item["loc"]) for item in error.errors()]
        return problem_response(
            request,
            422,
            "validation_failed",
            "Validation Failed",
            f"Invalid fields: {', '.join(fields)}",
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, _: IntegrityError) -> JSONResponse:
        return problem_response(request, 409, "resource_conflict", "Conflict", "Resource conflict.")

    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        return problem_response(
            request,
            error.status_code,
            "http_error",
            "HTTP Error",
            error.detail if isinstance(error.detail, str) else str(error.detail),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, error: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger.exception("unexpected_error", extra={"request_id": request_id})
        return problem_response(
            request, 500, "internal_error", "Internal Server Error", "An unexpected error occurred."
        )

    from app.api.routers import (
        operations,
    )

    app.include_router(health.router)
    app.include_router(identity.router, prefix="/api/v1")
    app.include_router(tasks.router, prefix="/api/v1")
    app.include_router(jobs.router)
    app.include_router(jobs.global_jobs_router)
    app.include_router(websocket.router)
    app.include_router(ml.router)
    app.include_router(agent.router)
    app.include_router(datasets.router)
    app.include_router(operations.router)

    from app.core.metrics import setup_metrics

    setup_metrics(app)
    return app


app = create_app()
