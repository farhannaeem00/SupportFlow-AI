from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    knowledge_base_id: UUID
    uploaded_by: UUID | None
    original_filename: str
    content_type: str
    file_size: int
    checksum: str
    status: str
    error_message: str | None
    chunk_count: int
    created_at: datetime
    updated_at: datetime