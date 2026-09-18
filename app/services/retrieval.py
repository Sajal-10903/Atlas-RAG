from dataclasses import dataclass
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Chunk, Document
from app.services.llm import embed
from app.services.vector_store import search


@dataclass
class RetrievedChunk:
    chunk: Chunk
    filename: str
    score: float
    semantic_rank: int | None
    lexical_rank: int | None


async def retrieve(session: AsyncSession, query: str, document_ids: list[UUID] | None, limit: int = 6) -> tuple[list[RetrievedChunk], dict]:
    semantic = await search((await embed([query]))[0], document_ids, limit * 3)
    filters = ""
    params: dict = {"query": query, "limit": limit * 3}
    if document_ids:
        filters = "AND c.document_id = ANY(CAST(:document_ids AS uuid[]))"
        params["document_ids"] = [str(v) for v in document_ids]
    # PostgreSQL FTS complements embeddings and keeps exact identifiers/names retrievable.
    sql = text(f"""
        SELECT c.id FROM chunks c
        WHERE to_tsvector('english', c.content) @@ websearch_to_tsquery('english', :query) {filters}
        ORDER BY ts_rank(to_tsvector('english', c.content), websearch_to_tsquery('english', :query)) DESC
        LIMIT :limit
    """)
    lexical = [UUID(str(row[0])) for row in (await session.execute(sql, params)).all()]
    ranks: dict[UUID, dict[str, int]] = {}
    for i, (id_, _) in enumerate(semantic, 1): ranks.setdefault(id_, {})["semantic"] = i
    for i, id_ in enumerate(lexical, 1): ranks.setdefault(id_, {})["lexical"] = i
    # Reciprocal Rank Fusion is stable across different score scales.
    fused = sorted(ranks, key=lambda id_: sum(1 / (60 + r) for r in ranks[id_].values()), reverse=True)[:limit]
    if not fused:
        return [], {"semantic_candidates": 0, "lexical_candidates": 0, "fusion": "rrf"}
    result = await session.execute(text("SELECT c.id, c.document_id, c.ordinal, c.page, c.content, c.token_estimate, d.filename FROM chunks c JOIN documents d ON d.id=c.document_id WHERE c.id = ANY(CAST(:ids AS uuid[]))"), {"ids": [str(v) for v in fused]})
    by_id = {UUID(str(r[0])): r for r in result.all()}
    semantic_scores = dict(semantic)
    records = []
    for id_ in fused:
        r = by_id[id_]
        entity = Chunk(id=UUID(str(r[0])), document_id=UUID(str(r[1])), ordinal=r[2], page=r[3], content=r[4], token_estimate=r[5])
        records.append(RetrievedChunk(entity, r[6], sum(1 / (60 + v) for v in ranks[id_].values()), ranks[id_].get("semantic"), ranks[id_].get("lexical")))
    return records, {"semantic_candidates": len(semantic), "lexical_candidates": len(lexical), "fusion": "rrf", "semantic_scores": {str(k): v for k, v in semantic_scores.items()}}

