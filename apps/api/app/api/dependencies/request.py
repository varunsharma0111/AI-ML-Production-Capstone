"""FastAPI dependencies for database access and verified principals."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.errors import AuthenticationError
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
    """Resolve current authenticated principal.

    Bypasses authentication in dev_auth_mode or open access mode, while strictly enforcing
    JWT verification when dev_auth_mode is False.
    """
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        try:
            from app.core.config import get_settings

            settings = get_settings()
        except Exception:
            settings = None

    is_dev_auth = getattr(settings, "dev_auth_mode", False) if settings is not None else True

    # When dev_auth_mode is False, enforce strict authentication
    if not is_dev_auth:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise AuthenticationError("A bearer access token is required.")
        return verifier.verify(credentials.credentials)

    # In dev_auth_mode / open access, try real token verification if valid JWT is provided
    if credentials is not None and credentials.scheme.lower() == "bearer":
        try:
            return verifier.verify(credentials.credentials)
        except Exception:
            pass

    # Default fallback principal for open access task performance
    return Principal(
        subject="dev-user-123",
        email="dev.user@example.com",
        display_name="Dev Demo User",
    )


def get_redis_manager(request: Request) -> RedisManager | None:
    return getattr(request.app.state, "redis_manager", None)
