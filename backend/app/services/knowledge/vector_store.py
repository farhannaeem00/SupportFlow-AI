
from functools import lru_cache
from math import isfinite
from pathlib import Path
from uuid import UUID

import chromadb

from app.config import settings


@lru_cache(maxsize=1)
def _get_chroma_client(storage_path: str):
    """Create and reuse a persistent ChromaDB client for a storage path."""

    path = Path(storage_path)
    path.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(path=str(path))


def get_chroma_client():
    """Return the cached persistent ChromaDB client."""

    storage_path = str(Path(settings.vector_store_dir).resolve())
    return _get_chroma_client(storage_path)


def reset_chroma_client() -> None:
    """Clear the cached client, useful when changing storage configuration."""

    _get_chroma_client.cache_clear()


def get_collection_name(organization_id: UUID) -> str:
    """Create a stable organization-specific collection name."""

    return f"org_{organization_id.hex}"


def get_organization_collection(organization_id: UUID):
    """Get or create an organization's vector collection."""

    client = get_chroma_client()

    return client.get_or_create_collection(
        name=get_collection_name(organization_id),
        metadata={
            "organization_id": str(organization_id),
            "hnsw:space": "cosine",
        },
    )


def _validate_embeddings(
    chunks: list[str],
    embeddings: list[list[float]],
) -> None:
    """Validate chunk and embedding data before storing."""

    if len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings count must match")

    if any(not isinstance(chunk, str) or not chunk.strip() for chunk in chunks):
        raise ValueError("Chunks must contain non-empty strings")

    if not embeddings:
        return

    dimensions = len(embeddings[0])

    if dimensions == 0:
        raise ValueError("Embeddings cannot be empty")

    for embedding in embeddings:
        if len(embedding) != dimensions:
            raise ValueError("All embeddings must have the same dimensions")

        if any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not isfinite(value)
            for value in embedding
        ):
            raise ValueError("Embeddings must contain finite numeric values")


def store_document_chunks(
    organization_id: UUID,
    knowledge_base_id: UUID,
    document_id: UUID,
    chunks: list[str],
    embeddings: list[list[float]],
    filename: str,
) -> int:
    """Store document chunks and their embeddings."""

    if not chunks:
        if embeddings:
            raise ValueError("Chunks and embeddings count must match")
        return 0

    _validate_embeddings(chunks, embeddings)

    collection = get_organization_collection(organization_id)

    ids = [
        f"{document_id}_{index}"
        for index in range(len(chunks))
    ]

    metadatas = [
        {
            "organization_id": str(organization_id),
            "knowledge_base_id": str(knowledge_base_id),
            "document_id": str(document_id),
            "chunk_index": index,
            "filename": filename,
        }
        for index in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return len(chunks)


def search_document_chunks(
    organization_id: UUID,
    knowledge_base_id: UUID,
    query_embedding: list[float],
    limit: int = 5,
) -> list[dict]:
    """Search for chunks belonging to one organization's knowledge base."""

    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 20:
        raise ValueError("Search limit must be between 1 and 20")

    _validate_embeddings(["query"], [query_embedding])

    collection = get_organization_collection(organization_id)

    total_chunks = collection.count()

    if total_chunks == 0:
        return []

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(limit, total_chunks),
        where={
            "$and": [
                {"organization_id": str(organization_id)},
                {"knowledge_base_id": str(knowledge_base_id)},
            ]
        },
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents") or [[]]
    metadatas = results.get("metadatas") or [[]]
    distances = results.get("distances") or [[]]

    if not documents or not metadatas or not distances:
        return []

    rows = zip(documents[0], metadatas[0], distances[0])

    return [
        {
            "text": document,
            "metadata": metadata,
            "distance": distance,
        }
        for document, metadata, distance in rows
        if isinstance(document, str)
        and isinstance(metadata, dict)
        and isinstance(distance, (int, float))
        and not isinstance(distance, bool)
        and isfinite(distance)
    ]


def delete_document_chunks(
    organization_id: UUID,
    document_id: UUID,
) -> None:
    """Delete all chunks belonging to one organization's document."""

    collection = get_organization_collection(organization_id)

    collection.delete(
        where={
            "$and": [
                {"document_id": str(document_id)},
                {"organization_id": str(organization_id)},
            ]
        }
    )


def delete_knowledge_base_chunks(
    organization_id: UUID,
    knowledge_base_id: UUID,
) -> None:
    """Delete all vector chunks belonging to an organization's knowledge base."""

    collection = get_organization_collection(organization_id)

    collection.delete(
        where={
            "$and": [
                {"organization_id": str(organization_id)},
                {"knowledge_base_id": str(knowledge_base_id)},
            ]
        }
    )
