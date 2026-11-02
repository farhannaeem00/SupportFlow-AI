import io
import re
from pathlib import Path

from docx import Document
from pypdf import PdfReader

from app.config import settings


def extract_pdf_text(content: bytes) -> str:
    """Extract text from a PDF document."""

    reader = PdfReader(io.BytesIO(content))

    if reader.is_encrypted:
        raise ValueError("Encrypted PDF documents are not supported")

    pages = []

    for page in reader.pages:
        text = page.extract_text() or ""

        if text.strip():
            pages.append(text)

    return "\n\n".join(pages)


def extract_docx_text(content: bytes) -> str:
    """Extract paragraphs and table text from a DOCX document."""

    document = Document(io.BytesIO(content))

    sections = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            sections.append(paragraph.text)

    for table in document.tables:
        for row in table.rows:
            cells = [
                cell.text.strip()
                for cell in row.cells
                if cell.text.strip()
            ]

            if cells:
                sections.append(" | ".join(cells))

    return "\n\n".join(sections)


def extract_txt_text(content: bytes) -> str:
    """Extract UTF-8 text from a TXT document."""

    return content.decode("utf-8-sig")


def clean_text(text: str) -> str:
    """Normalize extracted document text."""

    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_document_text(
    filename: str,
    content: bytes,
) -> str:
    """Extract text according to the document extension."""

    extension = Path(filename).suffix.lower()

    if extension == ".pdf":
        text = extract_pdf_text(content)

    elif extension == ".docx":
        text = extract_docx_text(content)

    elif extension == ".txt":
        text = extract_txt_text(content)

    else:
        raise ValueError(
            f"Unsupported document extension: {extension}"
        )

    text = clean_text(text)

    if not text:
        raise ValueError(
            "No readable text was found in this document"
        )

    return text


def chunk_text(text: str) -> list[str]:
    """Split text into overlapping character-based chunks."""

    chunk_size = settings.document_chunk_size
    overlap = settings.document_chunk_overlap

    if chunk_size <= 0:
        raise ValueError("Chunk size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "Chunk overlap must be non-negative and smaller than chunk size"
        )

    text = clean_text(text)

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        if end < len(text):
            # Prefer splitting at a paragraph, sentence, or word boundary.
            minimum_boundary = start + int(chunk_size * 0.7)

            candidates = [
                text.rfind("\n\n", minimum_boundary, end),
                text.rfind(". ", minimum_boundary, end),
                text.rfind(" ", minimum_boundary, end),
            ]

            boundary = max(candidates)

            if boundary > start:
                end = boundary + 1

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        next_start = end - overlap

        # Avoid repeatedly splitting at the same position.
        if next_start <= start:
            next_start = start + chunk_size - overlap

        start = next_start

    return chunks