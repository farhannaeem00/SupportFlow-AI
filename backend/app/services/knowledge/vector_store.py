import re
from functools import lru_cache
from pathlib import Path
from uuid import UUID

import chromadb

from app.config import settings


@lru_cache(maxsize=1)
def get_chroma_client():
    """Create and reuse the persistent ChromaDB client."""

    storage_path = Path(settings.vector_store_dir).resolve()
    storage_path.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(
        path=str(storage_path)
    )


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
        return 0

    if len(chunks) != len(embeddings):
        raise ValueError("Chunks and embeddings count must match")

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
    organization_id,
    knowledge_base_id,
    query_embedding,
    limit=5,
):
    if limit < 1 or limit > 20:
        raise ValueError("Search limit must be between 1 and 20")

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

    return [
        {
            "text": document,
            "metadata": metadata,
            "distance": distance,
        }
        for document, metadata, distance in zip(
            documents[0],
            metadatas[0],
            distances[0],
        )
    ]


def delete_document_chunks(organization_id, document_id):
    collection = get_organization_collection(organization_id)

    collection.delete(
        where={
            "$and": [
                {"document_id": str(document_id)},
                {"organization_id": str(organization_id)},
            ]
        }
    )