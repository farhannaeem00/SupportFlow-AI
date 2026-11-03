
from app.services.knowledge.document_processor import (
    extract_document_text,
    chunk_text,
)


def test_extract_txt_document():
    result = extract_document_text(
        "support.txt",
        b"Customer support documentation.",
    )

    assert result == "Customer support documentation."


def test_extract_txt_removes_utf8_bom():
    result = extract_document_text(
        "support.txt",
        b"\xef\xbb\xbfSupport documentation.",
    )

    assert result == "Support documentation."


def test_extract_rejects_unsupported_extension():
    import pytest

    with pytest.raises(ValueError, match="Unsupported document extension"):
        extract_document_text(
            "support.exe",
            b"Some content",
        )


def test_extract_rejects_empty_document():
    import pytest

    with pytest.raises(ValueError, match="No readable text"):
        extract_document_text(
            "empty.txt",
            b"   ",
        )


def test_chunk_text_returns_chunks():
    from app.config import settings

    text = "Customer support information. " * 100
    chunks = chunk_text(text)

    assert len(chunks) > 1
    assert all(chunk.strip() for chunk in chunks)
    assert all(len(chunk) <= settings.document_chunk_size for chunk in chunks)


def test_chunk_text_returns_empty_list_for_empty_input():
    assert chunk_text("   ") == []
