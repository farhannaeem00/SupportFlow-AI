
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeBase
from app.services.knowledge.embedding_service import generate_query_embedding
from app.services.knowledge.vector_store import search_document_chunks


def retrieve_knowledge(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
    query: str,
    limit: int = 5,
) -> list[dict]:
    """Retrieve only knowledge chunks within the configured distance threshold."""

    query = query.strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty",
        )

    if len(query) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Search query cannot exceed 2000 characters",
        )

    if limit < 1 or limit > 20:
        raise HTTPException(
            status_code=400,
            detail="Limit must be between 1 and 20",
        )

    knowledge_base = db.scalar(
        select(KnowledgeBase).where(
            KnowledgeBase.id == knowledge_base_id,
            KnowledgeBase.organization_id == organization_id,
            KnowledgeBase.is_active.is_(True),
        )
    )

    if not knowledge_base:
        raise HTTPException(
            status_code=404,
            detail="Active knowledge base not found",
        )

    query_embedding = generate_query_embedding(query)

    results = search_document_chunks(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        query_embedding=query_embedding,
        limit=limit,
    )

    relevant_results = []

    for result in results:
        distance = result.get("distance")

        # Ignore malformed results rather than passing uncertain matches to the AI.
        if not isinstance(distance, (int, float)):
            continue

        if distance < 0 or distance > 2:
            continue

        if distance > settings.knowledge_max_distance:
            continue

        metadata = result.get("metadata") or {}

        relevant_results.append(
            {
                "text": result["text"],
                "source": metadata.get("filename"),
                "document_id": metadata.get("document_id"),
                "chunk_index": metadata.get("chunk_index"),
                "distance": distance,
            }
        )

    return relevant_results
