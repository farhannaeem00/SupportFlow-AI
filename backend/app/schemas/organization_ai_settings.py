
from pydantic import BaseModel, ConfigDict, Field


class OrganizationAISettingsUpdate(BaseModel):
    ai_enabled: bool | None = None
    suggestions_enabled: bool | None = None

    confidence_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )

    escalation_priority_level: int | None = Field(
        default=None,
        ge=1,
        le=4,
    )

    max_context_messages: int | None = Field(
        default=None,
        ge=1,
        le=50,
    )


class OrganizationAISettingsResponse(BaseModel):
    ai_enabled: bool
    suggestions_enabled: bool
    confidence_threshold: float
    escalation_priority_level: int
    max_context_messages: int

    model_config = ConfigDict(from_attributes=True)
