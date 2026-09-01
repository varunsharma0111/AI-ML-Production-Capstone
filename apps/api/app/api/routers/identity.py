"""Authenticated identity endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.request import get_authenticated_principal, get_session
from app.api.schemas.identity import CurrentUserResponse, WorkspaceMemberInfo
from app.db.repositories.identity import IdentityRepository
from app.domains.identity.principal import Principal

router = APIRouter(tags=["identity"])
_identity_repository = IdentityRepository()


@router.get("/me", response_model=CurrentUserResponse)
async def current_user(
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> CurrentUserResponse:
    user = await _identity_repository.get_or_create_user(session, principal)
    workspaces = await _identity_repository.get_user_workspaces(session, user.id)
    return CurrentUserResponse(
        id=user.id,
        subject=user.oidc_subject,
        email=user.email,
        display_name=user.display_name,
        workspaces=[WorkspaceMemberInfo(**w) for w in workspaces],
    )

