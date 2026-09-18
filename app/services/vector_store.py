from uuid import UUID
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, Filter, FieldCondition, MatchAny, PointStruct, VectorParams
from app.config import get_settings


def qdrant() -> AsyncQdrantClient:
    return AsyncQdrantClient(url=get_settings().qdrant_url)


async def ensure_collection() -> None:
    s = get_settings()
    client = qdrant()
    if not await client.collection_exists(s.qdrant_collection):
        await client.create_collection(s.qdrant_collection, vectors_config=VectorParams(size=s.embedding_dimensions, distance=Distance.COSINE))


async def upsert(points: list[tuple[UUID, UUID, list[float]]]) -> None:
    s = get_settings()
    await qdrant().upsert(s.qdrant_collection, [PointStruct(id=str(chunk_id), vector=vector, payload={"document_id": str(doc_id)}) for chunk_id, doc_id, vector in points])


async def search(vector: list[float], document_ids: list[UUID] | None, limit: int) -> list[tuple[UUID, float]]:
    s = get_settings()
    filt = None
    if document_ids:
        filt = Filter(must=[FieldCondition(key="document_id", match=MatchAny(any=[str(v) for v in document_ids]))])
    hits = await qdrant().search(s.qdrant_collection, query_vector=vector, query_filter=filt, limit=limit)
    return [(UUID(str(hit.id)), float(hit.score)) for hit in hits]

