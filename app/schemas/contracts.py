from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    filename: str
    status: str
    chunk_count: int
    error: str | None = None
    created_at: datetime | None = None


class DocumentList(BaseModel):
    items: list[DocumentOut]


class ChatRequest(BaseModel):
    question: str = Field(min_length=3, max_length=8000)
    document_ids: list[UUID] | None = None
    top_k: int = Field(default=6, ge=1, le=20)


class Citation(BaseModel):
    ref: str
    document_id: UUID
    filename: str
    chunk_id: UUID
    page: int | None = None
    excerpt: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]
    retrieval_trace: dict


class ReportRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=8000)
    document_ids: list[UUID] | None = None
    format: str = Field(default="executive", pattern="^(executive|technical|brief)$")


class ReportResponse(BaseModel):
    report: str
    citations: list[Citation]
    steps: list[str]
