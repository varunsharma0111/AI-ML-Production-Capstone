"""FastAPI dependencies for database access and verified principals."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.redis import RedisManager
from app.core.security import JwtVerifier
from app.db.session import session_from_factory
from app.domains.identity.principal import Principal

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

bearer_scheme = HTTPBearer(auto_error=False)


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    return cast(async_sessionmaker[AsyncSession], request.app.state.session_factory)


async def get_session(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> AsyncIterator[AsyncSession]:
    async for session in session_from_factory(session_factory):
        yield session


def get_token_verifier(request: Request) -> JwtVerifier:
    return cast(JwtVerifier, request.app.state.token_verifier)


def get_request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", ""))


def get_authenticated_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    verifier: JwtVerifier = Depends(get_token_verifier),
) -> Principal:
    """Resolve current authenticated principal with PUBLIC_TEST_MODE & DEV_AUTH_MODE support."""
    settings = getattr(request.app.state, "settings", None)
    public_mode = settings and getattr(settings, "public_test_mode", False)

    if credentials is not None and credentials.scheme.lower() == "bearer":
        try:
            return verifier.verify(credentials.credentials)
        except Exception:
            if public_mode:
                return Principal(
                    subject="public-test-user-id",
                    email="public.test@auraml.local",
                    display_name="Public Test User",
                )
            raise

    if public_mode:
        return Principal(
            subject="public-test-user-id",
            email="public.test@auraml.local",
            display_name="Public Test User",
        )

    if settings and getattr(settings, "dev_auth_mode", False):
        return Principal(
            subject="dev-user-123",
            email="dev.user@example.com",
            display_name="Dev Demo User",
        )

    from app.core.errors import AuthenticationError

    raise AuthenticationError()


def get_redis_manager(request: Request) -> RedisManager | None:
    return getattr(request.app.state, "redis_manager", None)
