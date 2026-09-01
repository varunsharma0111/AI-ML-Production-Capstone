"""Authenticated identity endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.request import get_authenticated_principal, get_session
from app.api.schemas.identity import CurrentUserResponse
from app.domains.identity.principal import Principal
from app.services.tasks import TaskService

router = APIRouter(tags=["identity"])
_task_service = TaskService()


@router.get("/me", response_model=CurrentUserResponse)
async def current_user(
    principal: Principal = Depends(get_authenticated_principal),
    session: AsyncSession = Depends(get_session),
) -> CurrentUserResponse:
    user = await _task_service.current_user(session, principal)
    return CurrentUserResponse(
        id=user.id,
        subject=user.oidc_subject,
        email=user.email,
        display_name=user.display_name,
    )
