from pathlib import Path
from uuid import uuid4, UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.research import answer, create_report
from app.config import get_settings
from app.db import get_session
from app.models import Document
from app.schemas.contracts import (
    ChatRequest,
    ChatResponse,
    DocumentList,
    DocumentOut,
    ReportRequest,
    ReportResponse,
)
from app.services.extraction import SUPPORTED_EXTENSIONS
from app.services.ingestion import ingest


router = APIRouter(prefix="/api/v1")


@router.post("/documents", response_model=DocumentOut, status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    settings = get_settings()

    filename = Path(file.filename or "upload").name

    if Path(filename).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            415,
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    content = await file.read()

    if not content:
        raise HTTPException(422, "Empty uploads are not supported")

    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(
            413,
            f"Upload exceeds {settings.max_upload_mb} MB",
        )

    target = Path(settings.upload_dir) / f"{uuid4()}_{filename}"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)

    document = Document(
        filename=filename,
        content_type=file.content_type or "application/octet-stream",
        storage_path=str(target),
    )

    session.add(document)
    await session.commit()
    await session.refresh(document)

    # Run ingestion after the 202 response is sent.
    background_tasks.add_task(ingest, document.id)

    return document


@router.get("/documents", response_model=DocumentList)
async def list_documents(
    session: AsyncSession = Depends(get_session),
):
    documents = (
        await session.scalars(
            select(Document)
            .order_by(Document.created_at.desc())
            .limit(100)
        )
    ).all()

    # Explicitly convert SQLAlchemy ORM objects to Pydantic models.
    return DocumentList(
        items=[
            DocumentOut.model_validate(document)
            for document in documents
        ]
    )


@router.get("/documents/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    document = await session.get(Document, document_id)

    if not document:
        raise HTTPException(404, "Document not found")

    return document


@router.post("/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        result, refs, trace = await answer(
            session,
            payload.question,
            payload.document_ids,
            payload.top_k,
        )

        return ChatResponse(
            answer=result,
            citations=refs,
            retrieval_trace=trace,
        )

    except RuntimeError as exc:
        raise HTTPException(503, str(exc))


@router.post("/reports", response_model=ReportResponse)
async def report(
    payload: ReportRequest,
    session: AsyncSession = Depends(get_session),
):
    try:
        result, refs, steps = await create_report(
            session,
            payload.topic,
            payload.document_ids,
            payload.format,
        )

        return ReportResponse(
            report=result,
            citations=refs,
            steps=steps,
        )

    except RuntimeError as exc:
        raise HTTPException(503, str(exc))