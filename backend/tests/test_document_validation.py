
import io
import zipfile
import uuid

import pytest
from fastapi import HTTPException

import app.services.knowledge_document_service as service
from app.services.knowledge_document_service import validate_file


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


@pytest.mark.parametrize(
    "unsafe_name",
    [
        "../outside.txt",
        "/outside.txt",
        "folder/../outside.txt",
    ],
)
def test_docx_unsafe_archive_paths_are_rejected(unsafe_name):
    content = make_docx({
        "[Content_Types].xml": "<Types/>",
        "word/document.xml": "<document/>",
        unsafe_name: "malicious content",
    })

    with pytest.raises(HTTPException) as exc:
        service.validate_file("document.docx", content)

    assert exc.value.status_code == 400


def test_docx_duplicate_archive_entries_are_rejected():
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
        archive.writestr("word/document.xml", "<malicious/>")

    with pytest.raises(HTTPException) as exc:
        service.validate_file("document.docx", buffer.getvalue())

    assert exc.value.status_code == 400


@pytest.mark.parametrize(
    "unsafe_filename",
    [
        "../outside.txt",
        "/outside.txt",
        "folder\\outside.txt",
        "folder/outside.txt",
    ],
)
def test_stored_document_path_rejects_unsafe_filenames(
    unsafe_filename,
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(service.settings, "upload_dir", str(tmp_path))

    with pytest.raises(HTTPException) as exc:
        service.get_stored_document_path(
            uuid.uuid4(),
            uuid.uuid4(),
            unsafe_filename,
        )

    assert exc.value.status_code == 400
def make_docx_with_raw_backslash():
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")

        entry = zipfile.ZipInfo("folder/outside.txt")
        entry.filename = "folder\\outside.txt"

        archive.writestr(entry, "malicious content")

    return buffer.getvalue()

def test_docx_windows_backslash_archive_path_is_rejected():
    content = make_docx_with_raw_backslash()

    with pytest.raises(HTTPException) as exc:
        validate_file("malicious.docx", content)

    assert exc.value.status_code == 400