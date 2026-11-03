from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


TeamRole = Literal["owner", "agent"]


class InviteMemberRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: TeamRole = "agent"


class UpdateMemberRoleRequest(BaseModel):
    role: TeamRole


class TeamMemberResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: TeamRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)