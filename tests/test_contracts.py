from types import SimpleNamespace
from uuid import uuid4
from app.schemas.contracts import DocumentList


def test_document_list_serializes_orm_style_rows():
    row = SimpleNamespace(id=uuid4(), filename="source.pdf", status="ready", chunk_count=2, error=None, created_at=None)
    result = DocumentList(items=[row])
    assert result.items[0].filename == "source.pdf"
