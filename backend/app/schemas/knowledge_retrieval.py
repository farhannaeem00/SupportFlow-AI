
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)


class KnowledgeSearchResult(BaseModel):
    text: str
    source: str | None
    document_id: UUID
    chunk_index: int
    distance: float


class KnowledgeSearchResponse(BaseModel):
    results: list[KnowledgeSearchResult]
    total: int
