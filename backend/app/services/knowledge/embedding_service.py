from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import settings


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """Load the embedding model once and reuse it."""

    return SentenceTransformer(settings.embedding_model)


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Convert text chunks into normalized embedding vectors."""

    if not texts:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    return embeddings.tolist()


def generate_query_embedding(text: str) -> list[float]:
    """Generate an embedding for a search query."""

    embeddings = generate_embeddings([text])

    return embeddings[0]