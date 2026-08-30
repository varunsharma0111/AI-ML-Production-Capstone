"""Transport schema for the verified current user."""

from uuid import UUID

from pydantic import BaseModel


class CurrentUserResponse(BaseModel):
    id: UUID
    subject: str
    email: str | None
    display_name: str | None
