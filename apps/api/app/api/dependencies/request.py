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

    Respects DEV_AUTH_MODE setting:
    - If DEV_AUTH_MODE is True: returns default dev principal if no Bearer token provided.
    - If DEV_AUTH_MODE is False: strictly verifies Bearer JWT; fails with 401 if missing/invalid.
    """
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        try:
            from app.core.config import get_settings

            settings = get_settings()
        except Exception:
            settings = None

    is_dev_auth = getattr(settings, "dev_auth_mode", True) if settings is not None else True

    # If valid Bearer credentials provided, attempt verification
    if credentials is not None and credentials.scheme.lower() == "bearer":
        try:
            return verifier.verify(credentials.credentials)
        except AuthenticationError:
            if not is_dev_auth:
                raise
        except Exception:
            if not is_dev_auth:
                raise AuthenticationError("Invalid authentication credentials.")

    # In production mode (DEV_AUTH_MODE=false), fail closed with 401 if missing credentials
    if not is_dev_auth:
        raise AuthenticationError("A bearer access token is required.")

    # Open access principal for DEV_AUTH_MODE=true
    return Principal(
        subject="dev-user-123",
        email="dev.user@example.com",
        display_name="Dev Demo User",
    )


def get_redis_manager(request: Request) -> RedisManager | None:
    return getattr(request.app.state, "redis_manager", None)
