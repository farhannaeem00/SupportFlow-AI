from uuid import UUID

from pydantic import BaseModel


class OrganizationContextResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    public_key: str
    role: str