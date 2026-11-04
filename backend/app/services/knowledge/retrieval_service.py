
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import KnowledgeBase, KnowledgeDocument
from app.services.knowledge.embedding_service import generate_query_embedding
from app.services.knowledge.vector_store import search_document_chunks


def retrieve_knowledge(
    db: Session,
    organization_id: UUID,
    knowledge_base_id: UUID,
    query: str,
    limit: int = 5,
) -> list[dict]:
    """Retrieve relevant chunks from successfully processed documents."""

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

    # Only documents that completed processing may contribute knowledge.
    processed_document_ids = db.scalars(
        select(KnowledgeDocument.id).where(
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.knowledge_base_id == knowledge_base_id,
            KnowledgeDocument.status == "processed",
        )
    ).all()

    if not processed_document_ids:
        return []

    query_embedding = generate_query_embedding(query)

    results = search_document_chunks(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        query_embedding=query_embedding,
        limit=limit,
        document_ids=processed_document_ids,
    )

    relevant_results = []

    for result in results:
        distance = result.get("distance")

        if not isinstance(distance, (int, float)):
            continue

        if isinstance(distance, bool):
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
