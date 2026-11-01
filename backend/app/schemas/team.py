from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class InviteMemberRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="agent")


class UpdateMemberRoleRequest(BaseModel):
    role: str


class TeamMemberResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)