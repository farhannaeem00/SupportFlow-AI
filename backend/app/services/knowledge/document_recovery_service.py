
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import KnowledgeDocument


def recover_stale_documents(db: Session | None = None) -> int:
    """
    Reset documents stuck in processing beyond the configured timeout.

    Returns the number of documents reset to uploaded.
    """

    owns_session = db is None

    if owns_session:
        db = SessionLocal()

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=settings.document_processing_timeout_minutes
        )

        statement = (
            update(KnowledgeDocument)
            .where(
                KnowledgeDocument.status == "processing",
                KnowledgeDocument.processing_started_at.is_not(None),
                KnowledgeDocument.processing_started_at < cutoff,
            )
            .values(
                status="uploaded",
                processing_started_at=None,
                chunk_count=0,
                error_message=(
                    "Document processing was interrupted. "
                    "The document is ready to be retried."
                ),
            )
        )

        result = db.execute(statement)
        recovered_count = result.rowcount or 0
        db.commit()

        return recovered_count

    except Exception:
        db.rollback()
        raise

    finally:
        if owns_session:
            db.close()
