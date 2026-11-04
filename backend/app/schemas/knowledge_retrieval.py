
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Search query cannot be empty")
        return value


class KnowledgeSearchResult(BaseModel):
    text: str
    source: str | None
    document_id: UUID
    chunk_index: int
    distance: float


class KnowledgeSearchResponse(BaseModel):
    results: list[KnowledgeSearchResult]
    total: int
