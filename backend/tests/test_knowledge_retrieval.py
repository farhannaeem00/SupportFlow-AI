
from uuid import uuid4

import pytest

from app.config import settings
from app.services.knowledge import retrieval_service
from types import SimpleNamespace


@pytest.fixture
def retrieval_context(monkeypatch):
    organization_id = uuid4()
    knowledge_base_id = uuid4()

    class FakeDB:
        def scalar(self, query):
            return object()

        def scalars(self, query):
            return SimpleNamespace(
                all=lambda: [uuid4()]
            )

    monkeypatch.setattr(
        retrieval_service,
        "generate_query_embedding",
        lambda query: [0.1, 0.2, 0.3],
    )

    return {
        "db": FakeDB(),
        "organization_id": organization_id,
        "knowledge_base_id": knowledge_base_id,
    }


def run_retrieval(monkeypatch, context, results):
    monkeypatch.setattr(
        retrieval_service,
        "search_document_chunks",
        lambda **kwargs: results,
    )

    return retrieval_service.retrieve_knowledge(
        db=context["db"],
        organization_id=context["organization_id"],
        knowledge_base_id=context["knowledge_base_id"],
        query="What is your refund policy?",
    )


def make_result(distance):
    return {
        "text": "Customers can request a refund within 30 days.",
        "metadata": {
            "filename": "refund-policy.pdf",
            "document_id": str(uuid4()),
            "chunk_index": 0,
        },
        "distance": distance,
    }


def test_retrieval_keeps_relevant_results(
    monkeypatch,
    retrieval_context,
):
    results = [
        make_result(0.15),
        make_result(0.35),
    ]

    retrieved = run_retrieval(
        monkeypatch,
        retrieval_context,
        results,
    )

    assert len(retrieved) == 2
    assert retrieved[0]["distance"] == 0.15
    assert retrieved[1]["distance"] == 0.35


def test_retrieval_rejects_irrelevant_results(
    monkeypatch,
    retrieval_context,
):
    results = [
        make_result(0.95),
        make_result(1.25),
    ]

    retrieved = run_retrieval(
        monkeypatch,
        retrieval_context,
        results,
    )

    assert retrieved == []


def test_retrieval_accepts_exact_threshold(
    monkeypatch,
    retrieval_context,
):
    retrieved = run_retrieval(
        monkeypatch,
        retrieval_context,
        [make_result(settings.knowledge_max_distance)],
    )

    assert len(retrieved) == 1


def test_retrieval_filters_mixed_results(
    monkeypatch,
    retrieval_context,
):
    results = [
        make_result(0.2),
        make_result(0.95),
        make_result(0.5),
    ]

    retrieved = run_retrieval(
        monkeypatch,
        retrieval_context,
        results,
    )

    assert len(retrieved) == 2
    assert all(
        result["distance"] <= settings.knowledge_max_distance
        for result in retrieved
    )


@pytest.mark.parametrize(
    "distance",
    [None, "0.2", -0.1, 2.1],
)
def test_retrieval_rejects_invalid_distances(
    monkeypatch,
    retrieval_context,
    distance,
):
    retrieved = run_retrieval(
        monkeypatch,
        retrieval_context,
        [make_result(distance)],
    )

    assert retrieved == []


def test_retrieval_returns_empty_when_no_processed_documents(
    monkeypatch,
    retrieval_context,
):
    monkeypatch.setattr(
        retrieval_context["db"],
        "scalars",
        lambda query: SimpleNamespace(all=lambda: []),
    )

    def unexpected_search(**kwargs):
        raise AssertionError(
            "ChromaDB must not be queried without processed documents"
        )

    monkeypatch.setattr(
        retrieval_service,
        "search_document_chunks",
        unexpected_search,
    )

    retrieved = run_retrieval(
        monkeypatch,
        retrieval_context,
        [],
    )

    assert retrieved == []


def test_retrieval_searches_only_processed_document_ids(
    monkeypatch,
    retrieval_context,
):
    processed_document_ids = [uuid4(), uuid4()]
    captured = {}

    monkeypatch.setattr(
        retrieval_context["db"],
        "scalars",
        lambda query: SimpleNamespace(
            all=lambda: processed_document_ids
        ),
    )

    def fake_search(**kwargs):
        captured.update(kwargs)
        return [make_result(0.2)]

    monkeypatch.setattr(
        retrieval_service,
        "search_document_chunks",
        fake_search,
    )

    retrieved = retrieval_service.retrieve_knowledge(
        db=retrieval_context["db"],
        organization_id=retrieval_context["organization_id"],
        knowledge_base_id=retrieval_context["knowledge_base_id"],
        query="What is your refund policy?",
    )

    assert len(retrieved) == 1
    assert captured["document_ids"] == processed_document_ids
