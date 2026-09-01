"""Transport schema for the verified current user."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel


class WorkspaceMemberInfo(BaseModel):
    id: UUID
    slug: str
    name: str
    role: str


class CurrentUserResponse(BaseModel):
    id: UUID
    subject: str
    email: str | None
    display_name: str | None
    workspaces: list[WorkspaceMemberInfo] = []
