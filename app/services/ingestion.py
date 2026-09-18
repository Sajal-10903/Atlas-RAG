import logging
from uuid import UUID
from app.db import SessionLocal
from app.models import Chunk, Document
from app.services.chunking import chunk
from app.services.extraction import extract
from app.services.llm import embed
from app.services.vector_store import upsert

logger = logging.getLogger(__name__)


async def ingest(document_id: UUID) -> None:
    """Run the complete local ingestion job and always leave a terminal status."""
    async with SessionLocal() as session:
        document = await session.get(Document, document_id)
        if not document:
            logger.warning("Ingestion skipped; document %s no longer exists", document_id)
            return
        document.status = "processing"
        document.error = None
        await session.commit()
        try:
            pieces = chunk(extract(document.storage_path))
            if not pieces:
                raise ValueError("No extractable text was found")
            rows = [Chunk(document_id=document.id, ordinal=i, page=p.page, content=p.content, token_estimate=max(1, len(p.content) // 4)) for i, p in enumerate(pieces)]
            session.add_all(rows)
            await session.flush()
            vectors = await embed([r.content for r in rows])
            await upsert([(r.id, document.id, vector) for r, vector in zip(rows, vectors)])
            document.chunk_count = len(rows)
            document.status = "ready"
            await session.commit()
            logger.info("Ingestion complete for %s: %s chunks", document_id, len(rows))
        except Exception as exc:
            # A failed flush/commit marks the transaction as unusable. Roll it back
            # before recording a durable, user-visible failure state.
            await session.rollback()
            failed_document = await session.get(Document, document_id)
            if failed_document:
                failed_document.status = "failed"
                failed_document.error = f"{type(exc).__name__}: {exc}"[:2000]
                await session.commit()
            logger.exception("Ingestion failed for %s", document_id)
