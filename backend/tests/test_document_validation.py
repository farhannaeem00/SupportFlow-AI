
import io
import zipfile

import pytest
from fastapi import HTTPException

import app.services.knowledge_document_service as service


def make_docx(entries=None):
    """Build a minimal DOCX-like ZIP archive for validation tests."""
    if entries is None:
        entries = {
            "[Content_Types].xml": "<Types/>",
            "word/document.xml": "<document/>",
        }

    buffer = io.BytesIO()

    with zipfile.ZipFile(
    buffer,
    "w",
    compression=zipfile.ZIP_DEFLATED,
) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)

    return buffer.getvalue()


def test_valid_docx_is_accepted():
    extension, content_type = service.validate_file(
        "document.docx",
        make_docx(),
    )

    assert extension == ".docx"
    assert content_type == service.CONTENT_TYPES[".docx"]


def test_invalid_docx_zip_is_rejected():
    with pytest.raises(HTTPException) as exc:
        service.validate_file("document.docx", b"not a zip archive")

    assert exc.value.status_code == 400


def test_docx_missing_required_entries_is_rejected():
    content = make_docx({
        "[Content_Types].xml": "<Types/>",
    })

    with pytest.raises(HTTPException) as exc:
        service.validate_file("document.docx", content)

    assert exc.value.status_code == 400


def test_docx_excessive_entry_count_is_rejected(monkeypatch):
    monkeypatch.setattr(service, "MAX_DOCX_ENTRIES", 3)

    content = make_docx({
        "[Content_Types].xml": "<Types/>",
        "word/document.xml": "<document/>",
        "word/styles.xml": "<styles/>",
        "word/settings.xml": "<settings/>",
    })

    with pytest.raises(HTTPException) as exc:
        service.validate_file("document.docx", content)

    assert exc.value.status_code == 400


def test_docx_excessive_total_uncompressed_size_is_rejected(monkeypatch):
    monkeypatch.setattr(
        service,
        "MAX_DOCX_TOTAL_UNCOMPRESSED_SIZE",
        100,
    )

    content = make_docx({
        "[Content_Types].xml": "<Types/>",
        "word/document.xml": "x" * 200,
    })

    with pytest.raises(HTTPException) as exc:
        service.validate_file("document.docx", content)

    assert exc.value.status_code == 400


def test_docx_excessive_individual_entry_size_is_rejected(monkeypatch):
    monkeypatch.setattr(service, "MAX_DOCX_ENTRY_SIZE", 50)

    content = make_docx({
        "[Content_Types].xml": "<Types/>",
        "word/document.xml": "x" * 100,
    })

    with pytest.raises(HTTPException) as exc:
        service.validate_file("document.docx", content)

    assert exc.value.status_code == 400


def test_docx_suspicious_compression_ratio_is_rejected(monkeypatch):
    monkeypatch.setattr(service, "MAX_DOCX_COMPRESSION_RATIO", 2)

    content = make_docx({
        "[Content_Types].xml": "<Types/>",
        "word/document.xml": "A" * 10000,
    })

    with pytest.raises(HTTPException) as exc:
        service.validate_file("document.docx", content)

    assert exc.value.status_code == 400
