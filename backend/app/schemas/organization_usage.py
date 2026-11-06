
from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class OrganizationUsageLimitsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_team_members: int | None = Field(default=None, ge=0)
    max_knowledge_bases: int | None = Field(default=None, ge=0)
    max_documents: int | None = Field(default=None, ge=0)
    max_storage_bytes: int | None = Field(default=None, ge=0)
    max_monthly_conversations: int | None = Field(default=None, ge=0)
    max_monthly_ai_operations: int | None = Field(default=None, ge=0)


class OrganizationUsageMetrics(BaseModel):
    team_members: int
    knowledge_bases: int
    documents: int
    storage_bytes: int
    monthly_conversations: int
    monthly_ai_operations: int
    monthly_ai_operations_reserved: int
    period_start: date


class OrganizationUsageLimits(BaseModel):
    team_members: int | None
    knowledge_bases: int | None
    documents: int | None
    storage_bytes: int | None
    monthly_conversations: int | None
    monthly_ai_operations: int | None


class OrganizationUsageResponse(BaseModel):
    usage: OrganizationUsageMetrics
    limits: OrganizationUsageLimits
