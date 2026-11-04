
from uuid import uuid4

import pytest

from app.services.knowledge import vector_store


class FakeCollection:
    def __init__(self):
        self.upsert_data = None
        self.query_data = None
        self.deleted = None
        self.total = 2

    def upsert(self, **kwargs):
        self.upsert_data = kwargs

    def get(self, **kwargs):
        requested_ids = kwargs["ids"]
        return {"ids": requested_ids}

    def count(self):
        return self.total

    def query(self, **kwargs):
        self.query_data = kwargs
        return {
            "documents": [["First chunk", "Second chunk"]],
            "metadatas": [
                [
                    {"filename": "first.pdf"},
                    {"filename": "second.pdf"},
                ]
            ],
            "distances": [[0.1, 0.2]],
        }

    def delete(self, **kwargs):
        self.deleted = kwargs


@pytest.fixture
def fake_collection(monkeypatch):
    collection = FakeCollection()

    monkeypatch.setattr(
        vector_store,
        "get_organization_collection",
        lambda organization_id: collection,
    )

    return collection


def test_collection_name_is_organization_specific():
    organization_id = uuid4()

    assert vector_store.get_collection_name(organization_id) == (
        f"org_{organization_id.hex}"
    )


def test_store_document_chunks_success(fake_collection):
    organization_id = uuid4()
    knowledge_base_id = uuid4()
    document_id = uuid4()

    count = vector_store.store_document_chunks(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
        chunks=["First chunk", "Second chunk"],
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
        filename="manual.pdf",
    )

    assert count == 2
    assert len(fake_collection.upsert_data["ids"]) == 2
    assert fake_collection.upsert_data["documents"] == [
        "First chunk",
        "Second chunk",
    ]


def test_store_empty_chunks_returns_zero(fake_collection):
    count = vector_store.store_document_chunks(
        organization_id=uuid4(),
        knowledge_base_id=uuid4(),
        document_id=uuid4(),
        chunks=[],
        embeddings=[],
        filename="empty.pdf",
    )

    assert count == 0
    assert fake_collection.upsert_data is None


@pytest.mark.parametrize(
    ("chunks", "embeddings", "message"),
    [
        (["First"], [], "count must match"),
        (["First", "Second"], [[0.1, 0.2]], "count must match"),
        ([""], [[0.1, 0.2]], "non-empty strings"),
        (["First"], [[]], "cannot be empty"),
        (["First"], [[0.1], [0.2]], "count must match"),
        (["First"], [[0.1, float("nan")]], "finite numeric"),
        (["First"], [[0.1, float("inf")]], "finite numeric"),
        (["First"], [[0.1, True]], "finite numeric"),
        (["First"], [[0.1, 0.2], [0.3, 0.4]], "count must match"),
    ],
)
def test_store_rejects_invalid_input(chunks, embeddings, message):
    with pytest.raises(ValueError, match=message):
        vector_store.store_document_chunks(
            organization_id=uuid4(),
            knowledge_base_id=uuid4(),
            document_id=uuid4(),
            chunks=chunks,
            embeddings=embeddings,
            filename="manual.pdf",
        )


def test_store_rejects_inconsistent_embedding_dimensions():
    with pytest.raises(ValueError, match="same dimensions"):
        vector_store.store_document_chunks(
            organization_id=uuid4(),
            knowledge_base_id=uuid4(),
            document_id=uuid4(),
            chunks=["First", "Second"],
            embeddings=[[0.1, 0.2], [0.3]],
            filename="manual.pdf",
        )


def test_search_document_chunks_success(fake_collection):
    organization_id = uuid4()
    knowledge_base_id = uuid4()

    results = vector_store.search_document_chunks(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        query_embedding=[0.1, 0.2],
        limit=5,
    )

    assert len(results) == 2
    assert results[0]["text"] == "First chunk"
    assert results[0]["metadata"]["filename"] == "first.pdf"
    assert results[0]["distance"] == 0.1


def test_search_uses_organization_and_knowledge_base_filters(fake_collection):
    organization_id = uuid4()
    knowledge_base_id = uuid4()

    vector_store.search_document_chunks(
        organization_id=organization_id,
        knowledge_base_id=knowledge_base_id,
        query_embedding=[0.1, 0.2],
    )

    filters = fake_collection.query_data["where"]["$and"]

    assert {"organization_id": str(organization_id)} in filters
    assert {"knowledge_base_id": str(knowledge_base_id)} in filters


@pytest.mark.parametrize("limit", [0, -1, 21, True, 1.5])
def test_search_rejects_invalid_limit(limit):
    with pytest.raises(ValueError, match="Search limit"):
        vector_store.search_document_chunks(
            organization_id=uuid4(),
            knowledge_base_id=uuid4(),
            query_embedding=[0.1, 0.2],
            limit=limit,
        )


def test_search_returns_empty_when_collection_is_empty(fake_collection):
    fake_collection.total = 0

    results = vector_store.search_document_chunks(
        organization_id=uuid4(),
        knowledge_base_id=uuid4(),
        query_embedding=[0.1, 0.2],
    )

    assert results == []
    assert fake_collection.query_data is None


def test_search_ignores_malformed_results(fake_collection):
    fake_collection.query = lambda **kwargs: {
        "documents": [["Valid", None, "Invalid distance"]],
        "metadatas": [[{"filename": "valid.pdf"}, {}, {"filename": "bad.pdf"}]],
        "distances": [[0.1, 0.2, float("nan")]],
    }

    results = vector_store.search_document_chunks(
        organization_id=uuid4(),
        knowledge_base_id=uuid4(),
        query_embedding=[0.1, 0.2],
    )

    assert len(results) == 1
    assert results[0]["text"] == "Valid"


def test_delete_document_chunks_uses_tenant_filter(fake_collection):
    organization_id = uuid4()
    document_id = uuid4()

    vector_store.delete_document_chunks(organization_id, document_id)

    filters = fake_collection.deleted["where"]["$and"]

    assert {"organization_id": str(organization_id)} in filters
    assert {"document_id": str(document_id)} in filters


def test_delete_knowledge_base_chunks_uses_tenant_filter(fake_collection):
    organization_id = uuid4()
    knowledge_base_id = uuid4()

    vector_store.delete_knowledge_base_chunks(
        organization_id,
        knowledge_base_id,
    )

    filters = fake_collection.deleted["where"]["$and"]

    assert {"organization_id": str(organization_id)} in filters
    assert {"knowledge_base_id": str(knowledge_base_id)} in filters


def test_store_verifies_all_chunk_ids(fake_collection):
    document_id = uuid4()

    count = vector_store.store_document_chunks(
        organization_id=uuid4(),
        knowledge_base_id=uuid4(),
        document_id=document_id,
        chunks=["First chunk", "Second chunk"],
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
        filename="manual.pdf",
    )

    expected_ids = [
        f"{document_id}_0",
        f"{document_id}_1",
    ]

    assert count == 2
    assert fake_collection.upsert_data["ids"] == expected_ids


def test_store_fails_when_chromadb_does_not_store_all_chunks(
    fake_collection,
):
    fake_collection.get = lambda **kwargs: {
        "ids": kwargs["ids"][:1]
    }

    with pytest.raises(RuntimeError, match="all expected document chunks"):
        vector_store.store_document_chunks(
            organization_id=uuid4(),
            knowledge_base_id=uuid4(),
            document_id=uuid4(),
            chunks=["First chunk", "Second chunk"],
            embeddings=[[0.1, 0.2], [0.3, 0.4]],
            filename="manual.pdf",
        )

    assert fake_collection.deleted is not None
    assert len(fake_collection.deleted["ids"]) == 2


def test_store_fails_and_cleans_up_when_verification_raises(
    fake_collection,
):
    def fail_verification(**kwargs):
        raise RuntimeError("Simulated ChromaDB read failure")

    fake_collection.get = fail_verification

    with pytest.raises(RuntimeError, match="Simulated ChromaDB read failure"):
        vector_store.store_document_chunks(
            organization_id=uuid4(),
            knowledge_base_id=uuid4(),
            document_id=uuid4(),
            chunks=["First chunk"],
            embeddings=[[0.1, 0.2]],
            filename="manual.pdf",
        )

    assert fake_collection.deleted is not None