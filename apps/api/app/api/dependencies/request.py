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
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    verifier: JwtVerifier = Depends(get_token_verifier),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("A bearer access token is required.")
    return verifier.verify(credentials.credentials)


def get_redis_manager(request: Request) -> RedisManager | None:
    return getattr(request.app.state, "redis_manager", None)
