from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


TeamRole = Literal["owner", "agent"]


class InviteMemberRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: TeamRole = "agent"

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 2:
            raise ValueError("Name must contain at least 2 characters")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password cannot contain only whitespace")
        return value


class UpdateMemberRoleRequest(BaseModel):
    role: TeamRole


class TeamMemberResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr
    role: TeamRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)